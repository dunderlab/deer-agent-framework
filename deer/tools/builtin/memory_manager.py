import os
import json
from typing import Any
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.schema.io import Return


@dataclass
class MemoryManager(ToolProvider):

    def load_storage(self) -> dict:
        if not os.path.exists(self.storage_filename):
            return {}
        try:
            with open(self.storage_filename, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If the file is corrupt, treat it as empty to avoid blocking the agent
            return {}

    def save_storage(self, data: dict):
        with open(self.storage_filename, "w") as f:
            json.dump(data, f, indent=2)

    @property
    def storage_filename(self):
        return self.jail / ".DEER_MEMORY.json"

    @tool(modifies_state=True)
    def store_key_insight(
        self, key: str, value: Any
    ) -> Return(success=bool, message=str):
        """Persists critical findings or configuration state in a JSON store within the jail. OVERWRITES existing values for the same key. Use this to maintain context across execution cycles."""
        data = self.load_storage()
        data[key] = value
        self.save_storage(data)
        return {"success": True, "message": f"Key '{key}' successfully stored."}

    @tool()
    def retrieve_key_insight(
        self, key: str
    ) -> Return(value=Any, exists=bool, message=str):
        """Retrieves a previously stored insight from the persistent JSON store. Essential for accessing facts or paths learned in earlier steps of the task."""
        data = self.load_storage()
        if key not in data:
            return {
                "value": None,
                "exists": False,
                "message": f"Key '{key}' not found in memory. Use list_memory_keys to see available keys.",
            }

        return {
            "value": data[key],
            "exists": True,
            "message": f"Key '{key}' retrieved successfully.",
        }

    @tool()
    def list_memory_keys(self) -> Return(keys=list[str], count=int):
        """Lists all keys currently active in the persistent store. Use this to audit available insights if the exact key names are forgotten."""
        data = self.load_storage()
        keys = list(data.keys())
        return {"keys": keys, "count": len(keys)}

    @tool(modifies_state=True)
    def clear_context_memory(self) -> Return(success=bool, message=str):
        """Permanently and IRREVERSIBLY deletes the memory store. Use this ONLY when pivoting to a completely unrelated task to avoid context pollution."""
        if os.path.exists(self.storage_filename):
            os.remove(self.storage_filename)
            return {"success": True, "message": "Memory cleared successfully."}
        return {"success": True, "message": "Memory was already empty."}
