from dataclasses import dataclass
from typing import Literal

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Case, CommandOut

# Use the Literal directly in the method signature to expose options to the agent
Command = Literal[
    "python", "python3", "gcc", "g++", "javac", "npm", "node", "jest", "vitest"
]
MAX_TIMEOUT = 300

# Standard response for rejected operations
REJECTED = {"stdout": "", "stderr": str, "returncode": -1, "message": str}


def _failure(message: str) -> dict:
    """Helper to construct a standardized failure response."""
    return {"stdout": "", "stderr": message, "returncode": -1, "message": message}


@dataclass
class CommandRunner(ToolProvider):
    """
    Provides capabilities to execute a restricted set of compilers,
    interpreters, and test runners within the jailed environment.
    """

    @tool(
        modifies_state=True,
        tests=[
            # Test: Invalid timeout (too low)
            Case(
                {"binary": "python3", "args": ["--version"], "timeout_seconds": 0},
                {**REJECTED, "message": str},
            ),
            # Test: Jailbreak attempt (path traversal)
            Case(
                {"binary": "python3", "args": ["--version"], "path": "../outside"},
                raises=Exception,
            ),
            # Test: Basic successful execution
            Case(
                {"binary": "python3", "args": ["-c", "print('hi')"]},
                {
                    "stdout": "hi\n",
                    "stderr": str,
                    "returncode": 0,
                    "message": str,
                },
            ),
        ],
    )
    def run_program(
        self,
        binary: Command,
        args: list[str],
        path: str = ".",
        timeout_seconds: int = 60,
    ) -> CommandOut:
        """Executes a specific binary to compile, test, or run scripts.
        Choose 'binary' from the allowed list. Pass flags and file paths as a list in 'args'.
        Set working directory via 'path' and execution time via 'timeout_seconds' (1-300s). Shell operators (;, &&, |, >, <) are NOT supported.
        """

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
            # We construct the command by quoting the binary and each argument.
            # This ensures that arguments containing spaces or special characters
            # are handled safely by the underlying run_command.
            import shlex

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
