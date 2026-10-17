from typing import List
import shlex
from deer.tools import ToolProvider
from deer.tools.schemas import CommandOut

MAX_TIMEOUT = 300


class BaseCommandRunner(ToolProvider):

    def _execute_command(
        self, binary: str, args: List[str], path: str, timeout_seconds: int = 60
    ) -> CommandOut:
        # 1. Validate path boundaries
        path = self.jailed_path(path)

        # 2. Validate timeout constraints
        if not 1 <= timeout_seconds <= MAX_TIMEOUT:
            return self._failure(
                f"timeout_seconds must be between 1 and {MAX_TIMEOUT}."
            )

        # 4. Execution
        try:
            safe_command = shlex.join([binary] + args)
            result = self.run_command(
                safe_command, cwd=path, timeout_seconds=timeout_seconds
            )
        except Exception as e:
            return self._failure(f"Execution error: {e}")

        # 5. Response formatting
        exit_code = result.get("returncode", -1)
        status_message = (
            "Command completed successfully."
            if exit_code == 0
            else f"Command failed with exit code {exit_code}."
        )
        return {**result, "message": status_message}
