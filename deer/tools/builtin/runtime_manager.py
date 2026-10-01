import shlex
from dataclasses import dataclass
from typing import Literal, TypeVar, Generic, List, Dict, Any

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Case, CommandOut

# --- Global Constants ---
MAX_TIMEOUT = 300
REJECTED = {"stdout": "", "stderr": str, "returncode": -1, "message": str}


def _failure(message: str) -> dict:
    """Helper to construct a standardized failure response."""
    return {"stdout": "", "stderr": message, "returncode": -1, "message": message}


# --- Specialized Command Sets ---
# We define Literals separately so each Agent sees only its relevant commands
DevCommand = Literal[
    "python", "python3", "gcc", "g++", "javac", "npm", "node", "jest", "vitest"
]

AdminCommand = Literal[
    "ls",
    "grep",
    "df",
    "du",
    "chmod",
    "chown",
    "curl",
    "wget",
    "tail",
    "cat",
    "mkdir",
    "rm",
    "ps",
    "top",
    "netstat",
    "ss",
]

# --- Base Logic ---


class BaseCommandRunner(ToolProvider):
    """
    Base class providing the core execution logic for command-line tools.
    Not intended to be used as a tool itself.
    """

    def _execute_command(
        self, binary: str, args: List[str], path: str, timeout_seconds: int
    ) -> CommandOut:
        # 1. Validate path boundaries
        self.jailed_path(path)

        # 2. Validate timeout constraints
        if not 1 <= timeout_seconds <= MAX_TIMEOUT:
            return _failure(f"timeout_seconds must be between 1 and {MAX_TIMEOUT}.")

        # 3. Verify binary exists in environment
        try:
            self.check_command(binary)
        except Exception as e:
            return _failure(f"Environment error: {e}")

        # 4. Execution
        try:
            safe_command = shlex.join([binary] + args)
            result = self.run_command(
                safe_command, cwd=path, timeout_seconds=timeout_seconds
            )
        except Exception as e:
            return _failure(f"Execution error: {e}")

        # 5. Response formatting
        exit_code = result.get("returncode", -1)
        status_message = (
            "Command completed successfully."
            if exit_code == 0
            else f"Command failed with exit code {exit_code}."
        )
        return {**result, "message": status_message}


# --- Specialized Tool Implementations ---


@dataclass
class DevCommandRunner(BaseCommandRunner):
    """
    Provides capabilities to execute development tools (compilers, interpreters)
    within the jailed environment.
    """

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"binary": "python3", "args": ["-c", "print('hi')"]},
                {"stdout": "hi\n", "stderr": str, "returncode": 0, "message": str},
            ),
        ],
    )
    def run_program(
        self,
        binary: DevCommand,
        args: List[str],
        path: str = ".",
        timeout_seconds: int = 60,
    ) -> CommandOut:
        """Executes a development binary to compile, test, or run scripts.
        Choose 'binary' from the dev-allowed list. Pass flags as a list in 'args'.
        Set working directory via 'path' and execution time via 'timeout_seconds' (1-300s).
        """
        return self._execute_command(binary, args, path, timeout_seconds)


@dataclass
class SysAdminRunner(BaseCommandRunner):
    """
    Provides capabilities to execute system administration tools
    within the jailed environment.
    """

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"binary": "ls", "args": ["-la"], "path": "."},
                {"stdout": str, "stderr": str, "returncode": 0, "message": str},
            ),
        ],
    )
    def run_program(
        self,
        binary: AdminCommand,
        args: List[str],
        path: str = ".",
        timeout_seconds: int = 60,
    ) -> CommandOut:
        """Executes a system administration binary.
        Choose 'binary' from the admin-allowed list. Pass flags as a list in 'args'.
        Set working directory via 'path' and execution time via 'timeout_seconds' (1-300s).
        """
        return self._execute_command(binary, args, path, timeout_seconds)
