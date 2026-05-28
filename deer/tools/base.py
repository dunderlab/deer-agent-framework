from abc import ABC, abstractmethod
from typing import Any, Type
from dataclasses import dataclass, field

from pydantic import BaseModel
from pathlib import Path
import subprocess
import shlex


class ToolProviderError(ValueError):
    pass


class CommandRunnerError(ValueError):
    pass


@dataclass
class ToolProvider:
    # jail: Path | str | None = field(default=None, kw_only=True)
    tools: list[str] | None = field(default=None, kw_only=True)

    def __post_init__(self):
        # pass
        self.jail_ = None

    @property
    def jail(self):
        assert self._jail is not None, (
            "Filesystem jail is not configured. "
            "The runtime cannot access the sandbox root path."
        )
        return self.jail_

    @jail.setter
    def jail(self, jail):
        self.jail_ = Path(jail).resolve(strict=True)

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
            raise ToolProviderError(
                f"Security breach: Path escapes jail: {resolved}"
            ) from None

        return resolved

    def run_command(
        self,
        command: str,
        *,
        cwd: str | Path,
        timeout_seconds: int = 30,
    ) -> dict:
        """Execute a command string without invoking a shell."""
        args = shlex.split(command)

        if not args:
            raise CommandRunnerError("Command cannot be empty.")

        safe_cwd = self.jail if cwd is None else self.jailed_path(cwd)

        completed = subprocess.run(
            args,
            cwd=safe_cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        return {
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }


class Tool(ABC):
    """Base contract for deterministic tools."""

    # input_schema: Type[Any] | None = None
    # output_schema: Type[Any] | None = None
    #
    # name: str = ""
    # description: str = ""
    # modifies_state: bool = False

    def __init__(self) -> None:
        if not self.name:
            self.name = self.__class__.__name__.lower()

    def validate_input(self, value: Any) -> Any:
        return self._validate_with_schema(self.params_type, value)

    def validate_output(self, value: Any) -> Any:
        return self._validate_with_schema(self.return_type, value)

    def _validate_with_schema(self, schema: Type[Any] | None, value: Any) -> Any:
        if schema is None:
            return value

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(value)

        return value

    @abstractmethod
    def run(self, params: dict[str, Any] | None = None) -> Any:
        """Execute the tool deterministically.

        Args:
            value: Main input value.
            params: Optional literal parameters.

        Returns:
            The deterministic output produced by the tool.
        """
        raise NotImplementedError
