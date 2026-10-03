from typing import List, get_args
import shlex
from deer.tools import ToolProvider
from deer.tools.schemas import CommandOut

# --- Global Constants ---
MAX_TIMEOUT = 300
REJECTED = {"stdout": "", "stderr": str, "returncode": -1, "message": str}


def _failure(message: str) -> dict:
    """Helper to construct a standardized failure response."""
    return {"stdout": "", "stderr": message, "returncode": -1, "message": message}


class BaseCommandRunner(ToolProvider):

    @property
    def allowed_commands(self):
        return list(get_args(self.availableCommands))

    def _execute_command(
        self, binary: str, args: List[str], path: str, timeout_seconds: int = 60
    ) -> CommandOut:
        # 1. Validate path boundaries
        path = self.jailed_path(path)

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
