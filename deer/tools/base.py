from abc import ABC, abstractmethod
from typing import Any, Type
from dataclasses import dataclass, field

from pydantic import BaseModel
from pathlib import Path
import subprocess
import shlex
import shutil


class ToolProviderError(ValueError):
    pass


class CommandRunnerError(ValueError):
    pass


@dataclass
class ToolProvider:
    tools: list[str] | None = field(default=None, kw_only=True)

    def __post_init__(self):
        # pass
        self.jail_ = None

        for command in self.commands or []:
            self.check_command(command)

    @property
    def commands(self):
        """Return the list of commands to be verified at agent startup."""
        return []

    @property
    def allowed_commands(self):
        """Return the list of allowed execution commands.

        If a command is not present in this list, its execution will fail
        at runtime.
        """
        return []

    @property
    def jail(self):
        assert self.jail_ is not None, (
            "Filesystem jail is not configured. "
            "The runtime cannot access the sandbox root path."
        )
        if not self.jail_.exists():
            self.jail_.mkdir(parents=True, exist_ok=True)
        return self.jail_

    @jail.setter
    def jail(self, jail):
        self.jail_ = Path(jail).resolve()

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

        try:
            args = shlex.split(command)
        except ValueError as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "message": f"Shell expansion error: {e}",
            }

        if not args:
            raise CommandRunnerError("Command cannot be empty.")

        if self.allowed_commands:
            is_allowed = False
            for allowed_cmd in self.allowed_commands:
                allowed_args = shlex.split(allowed_cmd)
                if (
                    len(args) >= len(allowed_args)
                    and args[: len(allowed_args)] == allowed_args
                ):
                    is_allowed = True
                    break

            if not is_allowed:
                return {
                    "stdout": "",
                    "stderr": f"Command '{command}' is not allowed.",
                    "returncode": -1,
                    "message": f"Security restriction: '{command}' is not in the allowed list or doesn't match an allowed prefix.",
                }

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
            "message": "",
        }

    def check_command(self, command: str | Path) -> None:
        """
        Validates if a command exists in the operating system.
        Raises CommandRunnerError if the executable is not found in the PATH.
        """
        # Convert to string for compatibility with Windows and Python < 3.12
        cmd_str = str(command)
        if shutil.which(cmd_str) is None:
            raise CommandRunnerError(
                f"The command '{cmd_str}' is not available on the system. "
                f"Please ensure it is installed and configured in your PATH."
            )


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
