import shlex
from dataclasses import dataclass
from typing import Literal

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case


@dataclass
class ProcessManager(ToolProvider):
    """
    Provides tools to monitor and control background system processes.
    Used for managing servers, long-running scripts, or cleaning up hung tasks.
    """

    @property
    def allowed_commands(self):
        return ["pgrep", "ps", "kill"]

    @tool(
        tests=[
            # Test: Process is running
            # Note: In a real test environment, 'sleep' is often used as a dummy process
            Case({"process_name": "sleep"}, {"running": bool, "message": str}),
            # Test: Process is definitely not running
            Case(
                {"process_name": "non_existent_process_xyz_123"},
                {"running": False, "message": str},
            ),
        ],
    )
    def is_process_running(
        self, process_name: str
    ) -> Return(running=bool, message=str):
        """Checks if a background process is currently active. Use this to verify if a service or script is still running."""

        if self.is_command_authorized("pgrep"):
            result = self.run_command(
                f"pgrep -x {shlex.quote(process_name)}",
                cwd=".",
                timeout_seconds=5,
            )
            return {
                "running": result["returncode"] == 0,
                "message": "Checked via pgrep.",
            }

        if self.is_command_authorized("ps"):
            result = self.run_command("ps -e", cwd=".", timeout_seconds=5)
            return {
                "running": process_name in result["stdout"],
                "message": "Checked via ps.",
            }

        return {
            "running": False,
            "message": "No process monitoring tools available in the environment.",
        }

    @tool(
        modifies_state=True,
        tests=[
            # Test: Successful termination
            Case(
                {"process_name": "sleep", "signal": "TERM"},
                {"success": bool, "message": str},
            ),
            # Test: Attempt to kill a non-existent process
            Case(
                {"process_name": "non_existent_process_xyz_123", "signal": "KILL"},
                {"success": False, "message": str},
            ),
        ],
    )
    def kill_process(
        self, process_name: str, signal: Literal["TERM", "KILL"]
    ) -> Return(success=bool, message=str):
        """Stops a running process by sending a termination signal. Use 'TERM' for a graceful stop or 'KILL' for an immediate force-stop."""

        safe_name = shlex.quote(process_name)
        command = f"kill -{signal} $(pgrep -x {safe_name})"

        result = self.run_command(
            command,
            cwd=".",
            timeout_seconds=5,
        )

        return {
            "success": result["returncode"] == 0,
            "message": (
                f"Process '{process_name}' signaled with {signal} successfully."
                if result["returncode"] == 0
                else "Process not found or could not be killed."
            ),
        }
