from deer.tools.decorators import tool
from deer.schema.io import Struct
from dataclasses import dataclass
from pathlib import Path


class FileManagerError(ValueError):
    pass


@dataclass
class FileManager:
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

    @tool(
        name="new_file",
        description="Creates a new file with the given content.",
    )
    def new_file(self, path: str, content: str) -> Struct(status=str):

        path = self.jailed_path(path)

        with open(path, "w") as f:
            f.write(content)
        return {
            "status": "success",
        }

    @tool(
        name="read_file",
        description="Reads the content of a file.",
    )
    def read_file(self, path: str) -> Struct(content=str):

        path = self.jailed_path(path)

        with open(path, "r") as f:
            content = f.read()
        return {
            "content": content,
        }
