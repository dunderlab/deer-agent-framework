from deer.tools import ToolProvider, tool, Return

from dataclasses import dataclass
from pathlib import Path


class FileManagerError(ValueError):
    pass


@dataclass
class FileManager(ToolProvider):
    jail: Path | str

    def __post_init__(self):
        # Resolve the jail to an absolute, real path immediately.
        # strict=True ensures the base jail directory actually exists.
        self.jail = Path(self.jail).resolve(strict=True)

    def jailed_path(self, path: str | Path) -> Path:
        """
        Validates and returns a safe path within the jail.

        1. If 'path' is relative, it's joined to the jail.
        2. If 'path' is absolute, it's checked for containment.
        3. All '..' and symlinks are resolved before validation.
        """
        path = Path(path)

        # Handle point 2: If relative, interpret it as inside the jail.
        # If absolute, it remains as is to be validated against the jail.
        if not path.is_absolute():
            path = self.jail / path

        # Handle point 1: Normalize "..", symlinks, etc.
        # strict=False allows the path to not exist yet (e.g., for creating files).
        resolved = path.resolve(strict=False)

        # Real containment verification
        try:
            # relative_to raises ValueError if 'resolved' is not a child of 'self.jail'
            resolved.relative_to(self.jail)
        except ValueError:
            raise FileManagerError(
                f"Security breach: Path escapes jail: {resolved}"
            ) from None

        return resolved

    @tool(modifies_state=True)
    def new_file(self, path: str, content: str) -> Return(status=str):
        """Creates a new file with the given content."""
        safe_path = self.jailed_path(path)

        safe_path.parent.mkdir(parents=True, exist_ok=True)

        with open(safe_path, "w") as f:
            f.write(content)

        return {
            "status": safe_path.exists(),
        }

    @tool()
    def read_file(self, path: str) -> Return(content=str):
        """Reads the content of a file."""
        safe_path = self.jailed_path(path)

        with open(safe_path, "r") as f:
            content = f.read()
        return {
            "content": content,
        }

    @tool(modifies_state=True)
    def delete_file(self, path: str) -> Return(status=str):
        """Deletes a file."""
        safe_path = self.jailed_path(path)

        if safe_path.is_file():
            safe_path.unlink()
        else:
            raise ValueError(f"'{path}' is not a file or does not exist.")

        return {
            "status": not safe_path.exists(),
        }

    @tool(modifies_state=True)
    def create_directory(self, path: str) -> Return(status=str):
        """Creates a directory."""
        safe_path = self.jailed_path(path)
        safe_path.mkdir(parents=True, exist_ok=True)
        return {"status": "success"}

    @tool()
    def get_file_info(self, filename: str) -> Return(
        exists=bool,
        size_bytes=int,
        is_dir=bool,
        is_file=bool,
        last_modified=float,
    ):
        """Retrieves metadata about a file or directory, including its existence, size, type, and modification time."""
        safe_path = self.jailed_path(filename)
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
    def directory_tree(self, path: str, max_depth: int = 3) -> Return(tree=dict):
        """Returns the directory structure as a nested dictionary."""
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
