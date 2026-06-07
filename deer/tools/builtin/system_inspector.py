import os
from typing import Optional
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.schema.io import Return

BLACKLIST_ENV_VARS = [
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "DEER_BACKEND",
    "DEER_BACKEND_MODEL",
]


@dataclass
class SystemInspector(ToolProvider):

    @property
    def commands(self):
        """Return the list of commands to be verified at agent startup."""
        return ["ps", "netstat"]

    @property
    def allowed_commands(self):
        return ["ps -aux", "netstat -tuln", "ss -tuln"]

    @tool()
    def get_environment_variable(self, name: str) -> Return(value=Optional[str]):
        """Retrieves the value of an environment variable. Fails (returns None) for sensitive keys (API keys, backend configs) to prevent credential leakage."""
        if name in BLACKLIST_ENV_VARS:
            return {"value": None}
        return {"value": os.environ.get(name)}

    @tool()
    def list_active_processes(self) -> Return(processes=str):
        """Captures a snapshot of all system processes. Use this to identify active background tasks or services that might conflict with current operations."""
        result = self.run_command("ps -aux", cwd=self.jail)
        if result["returncode"] != 0:
            return {"processes": f"Error: {result['stderr']}"}
        return {"processes": result["stdout"]}

    @tool()
    def check_network_sockets(self) -> Return(sockets=str):
        """Lists listening network ports and bound addresses. Essential for verifying if local servers, databases, or microservices are reachable."""
        # Try netstat first
        result = self.run_command("netstat -tuln", cwd=self.jail)
        if result["returncode"] != 0:
            # Fallback to ss if netstat fails
            result = self.run_command("ss -tuln", cwd=self.jail)

        if result["returncode"] != 0:
            return {"sockets": f"Error: {result['stderr']}"}
        return {"sockets": result["stdout"]}
