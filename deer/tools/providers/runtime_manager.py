from dataclasses import dataclass
from typing import Literal, List

from deer.tools import tool
from deer.tools.schemas import Case, CommandOut
from .base.base_command_runner import BaseCommandRunner


# --- Specialized Command Sets ---
# We define Literals separately so each Agent sees only its relevant commands
DevCommand = Literal[
    "python",
    "python3",
    "gcc",
    "g++",
    "javac",
    "npm",
    "node",
    "jest",
    "vitest",
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


# --- Specialized Tool Implementations ---


@dataclass
class DevCommandRunner(BaseCommandRunner):
    availableCommands = DevCommand

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"binary": "python3", "args": ["-c", "print('hi')"]},
                {"stdout": "hi\n", "stderr": str, "returncode": 0, "message": str},
            ),
            Case(
                {"binary": "git", "args": ["status"]},
                {
                    "stdout": str,
                    "stderr": "Command 'git status' is not allowed.",
                    "returncode": -1,
                    "message": "Command failed with exit code -1.",
                },
            ),
        ],
    )
    def run_dev_program(
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
    availableCommands = AdminCommand

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"binary": "ls", "args": ["-la"], "path": "."},
                {"stdout": str, "stderr": str, "returncode": 0, "message": str},
            ),
        ],
    )
    def run_admin_program(
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
