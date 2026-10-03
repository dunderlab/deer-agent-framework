import os
from typing import Optional, List, Dict
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case

# Sensitive variables that must never be exposed to the agent
BLACKLIST_ENV_VARS = {
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "DEER_BACKEND",
    "DEER_BACKEND_MODEL",
}


@dataclass
class SystemObserver(ToolProvider):
    """
    Provides read-only observability of the system state.
    Used for monitoring environment variables, network ports, resource usage, and global process lists.
    """

    @tool(
        tests=[
            # Test: Retrieve a known, safe environment variable
            Case({"name": "PATH"}, {"value": str}),
            # Test: Attempt to retrieve a blacklisted variable
            Case({"name": "GEMINI_API_KEY"}, {"value": None}),
            # Test: Attempt to retrieve a non-existent variable
            Case({"name": "NON_EXISTENT_VAR_XYZ_123"}, {"value": None}),
        ]
    )
    def get_env_var(self, name: str) -> Return(value=Optional[str]):
        """Retrieves the value of an environment variable. Returns None if the variable is sensitive or does not exist."""
        if name in BLACKLIST_ENV_VARS:
            return {"value": None}
        return {"value": os.environ.get(name)}

    @tool(
        tests=[
            # Test: Successful process listing
            Case({}, {"processes": list, "error": str}),
        ]
    )
    def list_all_processes(self) -> Return(processes=List[Dict[str, str]], error=str):
        """Returns a structured list of all currently active system processes. Use this to get a global overview of what is running."""
        result = self.run_command("ps aux", cwd=self.jail)

        if result["returncode"] != 0:
            return {
                "processes": [],
                "error": f"Failed to list processes: {result['stderr']}",
            }

        lines = result["stdout"].strip().split("\n")
        if len(lines) < 2:
            return {"processes": [], "error": "No processes found."}

        headers = lines[0].split(None, 10)

        processes = []
        for line in lines[1:]:
            parts = line.split(None, 10)
            if len(parts) == len(headers):
                processes.append(dict(zip(headers, parts)))

        return {
            "processes": processes,
            "error": "",
        }

    @tool(
        tests=[
            # Test: Successful socket listing
            Case({}, {"sockets": str}),
        ]
    )
    def list_open_ports(self) -> Return(sockets=str):
        """Lists listening network ports and bound addresses. Use this to verify if local servers or databases are reachable."""
        result = self.run_command("netstat -tuln", cwd=self.jail)
        if result["returncode"] != 0:
            result = self.run_command("ss -tuln", cwd=self.jail)

        if result["returncode"] != 0:
            return {"sockets": f"Error retrieving sockets: {result['stderr']}"}

        return {"sockets": result["stdout"]}

    @tool(
        tests=[
            # Test: Successful resource retrieval
            Case({}, {"cpu": str, "ram": str, "disk": str}),
        ]
    )
    def get_system_resources(self) -> Return(cpu=str, ram=str, disk=str):
        """Returns a snapshot of current system resource consumption (CPU, RAM, and Disk usage)."""
        cpu_res = self.run_command("top -l 1 | grep 'CPU usage'", cwd=self.jail)
        ram_res = self.run_command("top -l 1 | grep PhysMem", cwd=self.jail)
        disk_res = self.run_command("df -h /", cwd=self.jail)

        return {
            "cpu": cpu_res["stdout"].strip(),
            "ram": ram_res["stdout"].strip(),
            "disk": disk_res["stdout"].strip(),
        }
