from dataclasses import dataclass
import tomlkit
from typing import Any, Optional, Union
from deer.tools import ToolProvider, tool
from deer.schema import Return


@dataclass
class TOMLEditor(ToolProvider):
    """Provides surgical editing and introspection for TOML files, preserving comments and formatting."""

    def _get_nested(self, data: Any, path_parts: list[str]) -> Any:
        current = data
        for part in path_parts:
            current = current[part]
        return current

    def _set_nested(self, data: Any, path_parts: list[str], value: Any):
        current = data
        for i, part in enumerate(path_parts[:-1]):
            if part not in current:
                current[part] = tomlkit.table()
            current = current[part]

        last_part = path_parts[-1]
        current[last_part] = value

    @tool()
    def read_toml(
        self, path: str, toml_path: Optional[str] = None
    ) -> Return(value=Any, message=str):
        """Navigates and extracts data from a TOML file using dot-notation, preserving comments and original formatting style."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"value": None, "message": f"File {path} not found."}
            with open(safe_path, "r", encoding="utf-8") as f:
                data = tomlkit.load(f)

            if toml_path:
                parts = toml_path.split(".")
                value = self._get_nested(data, parts)
                return {"value": value, "message": "Success"}

            return {"value": dict(data), "message": "Success"}
        except Exception as e:
            return {"value": None, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def update_toml(
        self, path: str, toml_path: str, value: Any
    ) -> Return(success=bool, message=str):
        """Surgically updates or adds a value to a TOML path, creating missing tables automatically while preserving comments."""
        safe_path = self.jailed_path(path)
        try:
            if safe_path.exists():
                with open(safe_path, "r", encoding="utf-8") as f:
                    data = tomlkit.load(f)
            else:
                data = tomlkit.document()

            parts = toml_path.split(".")
            self._set_nested(data, parts, value)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(data))
            return {"success": True, "message": f"Updated {toml_path} in {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def remove_toml_key(
        self, path: str, toml_path: str
    ) -> Return(success=bool, message=str):
        """Surgically removes a key from a TOML table, ensuring file integrity and preservation of surrounding comments."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}
            with open(safe_path, "r", encoding="utf-8") as f:
                data = tomlkit.load(f)

            parts = toml_path.split(".")
            parent_parts = parts[:-1]
            last_part = parts[-1]

            parent = data if not parent_parts else self._get_nested(data, parent_parts)

            if last_part in parent:
                del parent[last_part]
            else:
                return {"success": False, "message": f"Key {toml_path} not found."}

            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(data))
            return {"success": True, "message": f"Removed {toml_path} from {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool()
    def list_toml_keys(
        self, path: str, toml_path: Optional[str] = None
    ) -> Return(keys=list, message=str):
        """Introspects a TOML table at a specific path and returns its keys to facilitate navigation."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"keys": [], "message": f"File {path} not found."}
            with open(safe_path, "r", encoding="utf-8") as f:
                data = tomlkit.load(f)

            target = data
            if toml_path:
                target = self._get_nested(data, toml_path.split("."))

            if hasattr(target, "keys"):
                return {"keys": list(target.keys()), "message": "Success"}
            else:
                return {"keys": [], "message": "Target is not a table."}
        except Exception as e:
            return {"keys": [], "message": f"Error: {str(e)}"}
