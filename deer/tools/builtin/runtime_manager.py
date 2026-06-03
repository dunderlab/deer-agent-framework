import shlex
from dataclasses import dataclass
from typing import Literal, get_args

from deer.tools import ToolProvider, tool, Return, CommandOut

Command = Literal["python", "python3", "gcc", "g++", "javac", "npm", "node"]


@dataclass
class RuntimeManager(ToolProvider):

    @property
    def allowed_commands(self):
        return list(get_args(Command))

    @tool()
    def execute_test_suite(self, command: Command, path: str = ".") -> CommandOut:
        """Runs explicit benchmark testing commands (e.g., 'pytest', 'npm test')."""
        args = shlex.split(command)
        if not args:
            return {
                "stdout": "",
                "stderr": "Empty command",
                "returncode": -1,
                "message": "Command cannot be empty.",
            }

        base_cmd = args[0]

        # 1. Security Check (Whitelist)
        if base_cmd not in self.allowed_commands:
            return {
                "stdout": "",
                "stderr": f"Command '{base_cmd}' is not allowed.",
                "returncode": -1,
                "message": f"Security restriction: '{base_cmd}' is not in the allowed list.",
            }

        # 2. Availability Check (JIT)
        try:
            self.check_command(base_cmd)
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "message": f"Environment error: {str(e)}",
            }

        # 3. Execution
        try:
            result = self.run_command(command, cwd=path, timeout_seconds=60)
            return {
                **result,
                "message": (
                    "Test suite execution completed."
                    if result["returncode"] == 0
                    else "Test suite failed."
                ),
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "message": f"Execution error: {str(e)}",
            }

    @tool()
    def compile_source_code(self, command: Command, path: str = ".") -> CommandOut:
        """Invokes strict language compilers (e.g., 'gcc', 'javac') on a targeted file."""
        args = shlex.split(command)
        if not args:
            return {
                "stdout": "",
                "stderr": "Empty command",
                "returncode": -1,
                "message": "Command cannot be empty.",
            }

        base_cmd = args[0]

        # 1. Security Check
        if base_cmd not in self.allowed_commands:
            return {
                "stdout": "",
                "stderr": f"Command '{base_cmd}' is not allowed.",
                "returncode": -1,
                "message": "Security restriction.",
            }

        # 2. Availability Check (JIT)
        try:
            self.check_command(base_cmd)
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "message": f"Compiler not found: {str(e)}",
            }

        # 3. Execution
        try:
            result = self.run_command(command, cwd=path, timeout_seconds=30)
            return {
                **result,
                "message": (
                    "Compilation successful."
                    if result["returncode"] == 0
                    else "Compilation failed."
                ),
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "message": f"Compilation error: {str(e)}",
            }

    @tool()
    def check_process_status(
        self, process_name: str
    ) -> Return(running=bool, message=str):
        """Queries the execution state of a background process or service inside the sandbox."""
        # For monitoring, we check which tool is available JIT
        try:
            if "pgrep" in self.allowed_commands:
                try:
                    self.check_command("pgrep")
                    result = self.run_command(
                        f"pgrep {process_name}", cwd=".", timeout_seconds=5
                    )
                    return {
                        "running": result["returncode"] == 0,
                        "message": f"Checked via pgrep.",
                    }
                except:
                    pass  # Fallback to ps

            if "ps" in self.allowed_commands:
                try:
                    self.check_command("ps")
                    result = self.run_command("ps -e", cwd=".", timeout_seconds=5)
                    return {
                        "running": process_name in result["stdout"],
                        "message": f"Checked via ps.",
                    }
                except:
                    pass

            return {
                "running": False,
                "message": "No process monitoring tools available.",
            }
        except Exception as e:
            return {"running": False, "message": f"Status check error: {str(e)}"}
