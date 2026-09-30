import os
from typing import Optional
from dataclasses import dataclass
import pandas as pd
from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return

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
        return [
            "ps aux",
            "netstat -tuln",
            "ss -tuln",
            "top -l 1",
            "df",
            "find",
            "ls",
        ]

    @tool()
    def get_environment_variable(self, name: str) -> Return(value=Optional[str]):
        """Retrieves the value of an environment variable. Fails (returns None) for sensitive keys (API keys, backend configs) to prevent credential leakage."""
        if name in BLACKLIST_ENV_VARS:
            return {"value": None}
        return {"value": os.environ.get(name)}

    @tool()
    def list_active_processes(
        self,
    ) -> Return(processes=list[dict], columns=list[str], error=str):
        """Captures a snapshot of all system processes and returns them as a structured list of records. Use this to identify active background tasks or services that might conflict with current operations."""

        result = self.run_command("ps aux", cwd=self.jail)

        if result["returncode"] != 0:
            return {
                "processes": pd.DataFrame(),
                "columns": [],
                "error": f"Error: {result['stderr']}",
            }

        # 1. Separamos la salida por líneas
        lines = result["stdout"].strip().split("\n")
        if not lines:
            return {
                "processes": pd.DataFrame(),
                "columns": [],
                "error": "No processes found",
            }

        # 2. Procesamos cada línea manualmente
        # split(None, 10) divide la línea en máximo 11 partes (10 cortes)
        # Esto asegura que la columna COMMAND conserve sus espacios internos.
        parsed_data = [line.split(None, 10) for line in lines]

        # 3. Creamos el DataFrame usando la primera línea como encabezado
        df = pd.DataFrame(parsed_data[1:], columns=parsed_data[0])

        column_mapping = {
            "USER": "User",
            "PID": "Process ID",
            "%CPU": "CPU %",
            "%MEM": "Memory %",
            "VSZ": "Virtual Size",
            "RSS": "Resident Set Size",
            "TTY": "Terminal",
            "STAT": "Status",
            "START": "Start Time",
            "TIME": "CPU Time",
            "COMMAND": "Command",
        }
        df = df.rename(columns=column_mapping)

        return {
            "processes": df.to_dict(orient="records"),
            "columns": df.columns.tolist(),
            "error": "",
        }

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

    @tool()
    def get_resource_usage(self) -> Return(cpu=str, ram=str, disk=str):
        """Returns the current system resource consumption. Useful for deciding if a heavy task can be executed."""
        cpu = self.run_command("top -l 1 | grep 'CPU usage'", cwd=self.jail)["stdout"]
        ram = self.run_command("top -l 1 | grep PhysMem", cwd=self.jail)["stdout"]
        disk = self.run_command("df -h /", cwd=self.jail)["stdout"]
        return {"cpu": cpu, "ram": ram, "disk": disk}
