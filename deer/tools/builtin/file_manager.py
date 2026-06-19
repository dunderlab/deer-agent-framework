from deer.tools import ToolProvider, tool
from deer.schema import Return

from dataclasses import dataclass
from pathlib import Path
import shutil


class FileManagerError(ValueError):
    pass


@dataclass
class FileManager(ToolProvider):

    @tool(modifies_state=True)
    def new_file(self, path: str, content: str) -> Return(exists=bool):
        """Writes literal content to a file at the specified path. OVERWRITES the file if it already exists. Automatically creates any missing parent directories. Returns existence confirmation."""
        safe_path = self.jailed_path(path)

        safe_path.parent.mkdir(parents=True, exist_ok=True)

        with open(safe_path, "w") as f:
            f.write(content)

        return {
            "exists": safe_path.exists(),
        }

    @tool()
    def read_file(self, path: str) -> Return(content=str):
        """Reads the complete content of a file. Decodes as UTF-8 by default; falls back to raw string representation of bytes if decoding fails. Fails if the path is a directory or does not exist."""
        safe_path = self.jailed_path(path)

        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(safe_path, "rb") as f:
                content = str(f.read())
        return {
            "content": content,
        }

    @tool(modifies_state=True)
    def delete_file(self, path: str) -> Return(success=bool):
        """Permanently deletes a file. Fails with a ValueError if the path points to a directory or does not exist. Does not affect parent directories. Returns success confirmation."""
        safe_path = self.jailed_path(path)

        if safe_path.is_file():
            safe_path.unlink()
        else:
            raise ValueError(f"'{path}' is not a file or does not exist.")

        return {
            "success": not safe_path.exists(),
        }

    @tool(modifies_state=True)
    def create_directory(self, path: str) -> Return(status=str):
        """Idempotent operation: creates the directory and all necessary parent directories. If the directory already exists, it completes successfully without making changes."""
        safe_path = self.jailed_path(path)
        safe_path.mkdir(parents=True, exist_ok=True)
        return {"status": "success"}

    @tool(modifies_state=True)
    def delete_directory(self, path: str) -> Return(success=bool):
        """Recursively and IRREVERSIBLY deletes a directory and all its contents (files and subdirectories). Fails with a ValueError if the path points to a file or does not exist. Returns success confirmation."""
        safe_path = self.jailed_path(path)

        if safe_path.is_dir():
            shutil.rmtree(safe_path)
        else:
            raise ValueError(f"'{path}' is not a directory or does not exist.")

        if safe_path == self.jail:
            self.jail.mkdir(parents=True, exist_ok=True)
            return {"success": True}
        else:
            return {
                "success": not safe_path.exists(),
            }

    @tool(modifies_state=True)
    def bulk_delete(
        self, paths: list[str]
    ) -> Return(num_deleted=int, num_errors=int, error_messages=list[str]):
        """Performs a bulk delete operation on a list of paths. Returns the number of successfully deleted files and any errors encountered."""
        num_deleted = 0
        num_errors = 0
        error_messages = []
        for path in paths:
            try:
                self.delete_file(path)
                num_deleted += 1
            except ValueError as e:
                num_errors += 1
                error_messages.append(str(e))
        return {
            "num_deleted": num_deleted,
            "num_errors": num_errors,
            "error_messages": error_messages,
        }

    @tool()
    def get_file_info(self, path: str) -> Return(
        exists=bool,
        size_bytes=int,
        is_dir=bool,
        is_file=bool,
        last_modified=float,
    ):
        """Retrieves system metadata for a path. Use this to verify existence and distinguish between files and directories before performing I/O operations."""
        safe_path = self.jailed_path(path)
        if not safe_path.exists():
            return {"exists": False}

        stats = safe_path.stat()
        return {
            "exists": True,
            "size_bytes": stats.st_size,
            "is_dir": safe_path.is_dir(),
            "is_file": safe_path.is_file(),
            "last_modified": stats.st_mtime,
        }

    @tool()
    def directory_tree(self, path: str, max_depth: int) -> Return(tree=dict):
        """Generates a structural map of the directory hierarchy. Useful for gaining spatial awareness of the project layout. Fails if the path is not a directory."""
        safe_path = self.jailed_path(path)

        if not safe_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        if not safe_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        def build_node(current_path: Path, depth: int = 0) -> dict:
            relative_path = current_path.relative_to(self.jail)

            node = {
                "name": current_path.name,
                "path": str(relative_path),
                "type": "directory" if current_path.is_dir() else "file",
            }

            if current_path.is_file():
                node["size_bytes"] = current_path.stat().st_size
                return node

            if depth >= max_depth:
                node["children"] = []
                node["truncated"] = True
                return node

            children = sorted(
                current_path.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )

            node["children"] = [build_node(child, depth + 1) for child in children]
            return node

        return {
            "tree": build_node(safe_path),
        }

    @tool(modifies_state=True)
    def patch_file(
        self, path: str, old_text: str, new_text: str
    ) -> Return(success=bool, num_replacements=int, message=str):
        """Performs a surgical text replacement. ONLY SUCCEEDS IF EXACTLY ONE match for 'old_text' is found. This strict requirement prevents accidental corruption from ambiguous or missing search strings."""
        safe_path = self.jailed_path(path)
        with open(safe_path, "r") as f:
            content = f.read()

        num_replacements = content.count(old_text)

        if num_replacements == 0:
            return {
                "success": False,
                "num_replacements": 0,
                "message": "Error: old_text not found in file.",
            }

        if num_replacements > 1:
            return {
                "success": False,
                "num_replacements": num_replacements,
                "message": f"Ambiguity Error: {num_replacements} occurrences of old_text found. Please provide a more specific text block.",
            }

        patched_content = content.replace(old_text, new_text)

        with open(safe_path, "w") as f:
            f.write(patched_content)

        return {
            "success": True,
            "num_replacements": 1,
            "message": "File patched successfully.",
        }
