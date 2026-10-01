from dataclasses import dataclass
from pathlib import Path
import shutil

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case


@dataclass
class FileManager(ToolProvider):

    @tool(
        modifies_state=True,
        tests=[
            Case({"path": "a.txt", "content": "hola"}, {"exists": True}),
            Case({"path": "a/b/c.txt", "content": "hola"}, {"exists": True}),
        ],
    )
    def new_file(self, path: str, content: str) -> Return(exists=bool):
        """Writes literal content to a file at the specified path. OVERWRITES the file if it already exists.
        Automatically creates any missing parent directories. Returns existence confirmation.
        """
        safe_path = self.jailed_path(path)

        safe_path.parent.mkdir(parents=True, exist_ok=True)

        with open(safe_path, "w") as f:
            f.write(content)

        return {
            "exists": safe_path.exists(),
        }

    @tool(
        tests=[
            Case(
                {"path": "notes/a.txt"},
                {"content": "hola"},
                files={"notes/a.txt": "hola"},
            ),
        ],
    )
    def read_file(self, path: str) -> Return(content=str):
        """Reads the complete content of a file. Decodes as UTF-8 by default; falls back to raw string representation of bytes if decoding fails.
        Fails if the path is a directory or does not exist."""
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

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "notes/a.txt"},
                {"success": True},
                files={"notes/a.txt": "hola"},
            ),
        ],
    )
    def delete_file(self, path: str) -> Return(success=bool):
        """Permanently deletes a file. Fails with a ValueError if the path points to a directory or does not exist.
        Does not affect parent directories. Returns success confirmation."""
        safe_path = self.jailed_path(path)

        if safe_path.is_file():
            safe_path.unlink()
        else:
            raise ValueError(f"'{path}' is not a file or does not exist.")

        return {
            "success": not safe_path.exists(),
        }

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a"},
                {"success": True},
            ),
        ],
    )
    def create_directory(self, path: str) -> Return(success=bool):
        """Idempotent operation: creates the directory and all necessary parent directories.
        If the directory already exists, it completes successfully without making changes.
        """
        safe_path = self.jailed_path(path)
        safe_path.mkdir(parents=True, exist_ok=True)
        return {"success": True}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a"},
                {"success": True},
                dirs=["a"],
            ),
        ],
    )
    def delete_directory(self, path: str) -> Return(success=bool):
        """Recursively and IRREVERSIBLY deletes a directory and all its contents (files and subdirectories).
        Fails with a ValueError if the path points to a file or does not exist. Returns success confirmation.
        """
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

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"paths": ["a", "b", "c", "d"]},
                {"num_deleted": 2, "num_errors": 2, "error_messages": list[str]},
                files={"a": "a", "c": "c"},
            ),
        ],
    )
    def bulk_delete(
        self, paths: list[str]
    ) -> Return(num_deleted=int, num_errors=int, error_messages=list[str]):
        """Performs a bulk delete operation on a list of paths.
        Returns the number of successfully deleted files and any errors encountered."""
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

    @tool(
        tests=[
            Case(
                {"path": "a"},
                {
                    "exists": True,
                    "size_bytes": int,
                    "is_dir": False,
                    "is_file": True,
                    "last_modified": float,
                },
                files={"a": "a"},
            ),
            Case(
                {"path": "b"},
                {
                    "exists": False,
                    "size_bytes": int,
                    "is_dir": bool,
                    "is_file": bool,
                    "last_modified": float,
                },
            ),
            Case(
                {"path": "c"},
                {
                    "exists": True,
                    "size_bytes": int,
                    "is_dir": True,
                    "is_file": False,
                    "last_modified": float,
                },
                dirs=["c"],
            ),
        ],
    )
    def get_file_info(self, path: str) -> Return(
        exists=bool,
        size_bytes=int,
        is_dir=bool,
        is_file=bool,
        last_modified=float | int,
    ):
        """Retrieves system metadata for a path. Use this to verify existence and distinguish between files and directories before performing I/O operations."""
        safe_path = self.jailed_path(path)
        if not safe_path.exists():
            return {
                "exists": False,
                "size_bytes": 0,
                "is_dir": False,
                "is_file": False,
                "last_modified": 0.0,
            }

        stats = safe_path.stat()
        return {
            "exists": True,
            "size_bytes": stats.st_size,
            "is_dir": safe_path.is_dir(),
            "is_file": safe_path.is_file(),
            "last_modified": stats.st_mtime,
        }

    @tool(
        tests=[
            Case(
                {"path": "a", "max_depth": 99},
                {
                    "tree": "a/\n├── b/\n│   └── c/\n├── d/\n└── e/\n    └── f/\n        └── g/\n            └── h/\n                └── i/\n                    └── j/"
                },
                dirs=["a", "a/b/c", "a/d", "a/e/f/g/h/i/j"],
            ),
            Case(
                {"path": "a", "max_depth": 2},
                {"tree": "a/\n├── b/\n│   └── c/\n├── d/\n└── e/\n    └── f/"},
                dirs=["a", "a/b/c", "a/d", "a/e/f/g/h/i/j"],
            ),
        ],
    )
    def directory_tree(self, path: str, max_depth: int) -> Return(tree=str):
        """Generates a structural map of the directory hierarchy. Useful for gaining spatial awareness of the project layout.
        Fails if the path is not a directory."""

        safe_path = self.jailed_path(path)

        if not safe_path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        if not safe_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        lines = [f"{path}/"]

        def walk(current: Path, prefix: str, depth: int) -> None:
            if depth >= max_depth:
                return

            children = sorted(
                current.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )

            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                connector = "└── " if is_last else "├── "
                name = f"{child.name}/" if child.is_dir() else child.name
                lines.append(f"{prefix}{connector}{name}")

                if child.is_dir():
                    walk(child, prefix + ("    " if is_last else "│   "), depth + 1)

        walk(safe_path, "", 0)

        return {"tree": "\n".join(lines)}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.txt", "old_text": "a", "new_text": "b"},
                {"success": False, "num_replacements": 2, "message": str},
                files={"a.txt": "aa"},
            ),
            Case(
                {
                    "path": "a.txt",
                    "old_text": "a",
                    "new_text": "b",
                    "replace_all": True,
                },
                {"success": True, "num_replacements": 2, "message": str},
                files={"a.txt": "a-a"},
            ),
        ],
    )
    def patch_file(
        self, path: str, old_text: str, new_text: str, replace_all: bool = False
    ) -> Return(success=bool, num_replacements=int, message=str):
        """Performs a text replacement in a file. By default it ONLY SUCCEEDS IF EXACTLY ONE match for 'old_text' is found,
        which prevents accidental corruption from ambiguous search strings. Set replace_all=True to replace every occurrence.
        """
        safe_path = self.jailed_path(path)

        if not old_text:
            return {
                "success": False,
                "num_replacements": 0,
                "message": "old_text must not be empty.",
            }

        content = safe_path.read_text()
        num_matches = content.count(old_text)

        if num_matches == 0:
            return {
                "success": False,
                "num_replacements": 0,
                "message": "old_text not found in file.",
            }

        if num_matches > 1 and not replace_all:
            return {
                "success": False,
                "num_replacements": num_matches,
                "message": (
                    f"{num_matches} matches found, nothing changed. "
                    "Provide a more specific old_text or set replace_all=True."
                ),
            }

        safe_path.write_text(content.replace(old_text, new_text))

        return {
            "success": True,
            "num_replacements": num_matches,
            "message": f"Replaced {num_matches} occurrence(s).",
        }
