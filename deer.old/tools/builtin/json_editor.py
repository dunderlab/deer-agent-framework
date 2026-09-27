from dataclasses import dataclass
from ruamel.yaml import YAML
from typing import Any, Optional, Union
from deer.tools import ToolProvider, tool
from deer.schema import Return


@dataclass
class JSONEditor(ToolProvider):
    """Provides surgical editing for JSON files using ruamel.yaml to preserve structure and comments."""

    def __post_init__(self):
        super().__post_init__()
        # Use round-trip loader to preserve as much as possible
        self.yaml = YAML(typ="rt")
        # Ensure it writes in a way that is compatible with JSON if needed,
        # but the primary goal is preserving the input style.
        self.yaml.preserve_quotes = True

    def _get_nested(self, data: Any, path_parts: list[str]) -> Any:
        for part in path_parts:
            if isinstance(current, list):
                current = current[int(part)]
            else:
                current = current[part]
        return current

    def _set_nested(self, data: Any, path_parts: list[str], value: Any):
        current = data
        for i, part in enumerate(path_parts[:-1]):
            if isinstance(current, list):
                idx = int(part)
                current = current[idx]
            else:
                if part not in current:
                    next_part = path_parts[i + 1]
                    current[part] = [] if next_part.isdigit() else {}
                current = current[part]

        last_part = path_parts[-1]
        if isinstance(current, list):
            idx = int(last_part)
            while len(current) <= idx:
                current.append(None)
            current[idx] = value
        else:
            current[last_part] = value

    @tool()
    def read_json(
        self, path: str, json_path: Optional[str] = None
    ) -> Return(value=Any, message=str):
        """Navigates and extracts data from a JSON file using dot-notation while preserving original comments and formatting."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"value": None, "message": f"File {path} not found."}

            with open(safe_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            if json_path:
                parts = json_path.split(".")
                value = self._get_nested(data, parts)
                return {"value": value, "message": "Success"}

            return {"value": data, "message": "Success"}
        except Exception as e:
            return {"value": None, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def update_json(
        self, path: str, json_path: str, value: Any
    ) -> Return(success=bool, message=str):
        """Performs a surgical upsert on a JSON path, creating missing parent objects and preserving comments via round-trip parsing."""
        safe_path = self.jailed_path(path)
        try:
            if safe_path.exists():
                with open(safe_path, "r", encoding="utf-8") as f:
                    data = self.yaml.load(f)
            else:
                data = {}

            parts = json_path.split(".")
            self._set_nested(data, parts, value)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                # To ensure it stays as JSON-like as possible, we could use flow style,
                # but ruamel's round-trip usually detects the input style (braces vs no braces).
                self.yaml.dump(data, f)
            return {"success": True, "message": f"Updated {json_path} in {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def remove_json_key(
        self, path: str, json_path: str
    ) -> Return(success=bool, message=str):
        """Surgically removes a key or array element from a JSON file, maintaining structure and comments."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}

            with open(safe_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            parts = json_path.split(".")
            parent_parts = parts[:-1]
            last_part = parts[-1]

            parent = data if not parent_parts else self._get_nested(data, parent_parts)

            if isinstance(parent, list):
                parent.pop(int(last_part))
            else:
                parent.pop(last_part)

            with open(safe_path, "w", encoding="utf-8") as f:
                self.yaml.dump(data, f)
            return {"success": True, "message": f"Removed {json_path} from {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool()
    def list_json_keys(
        self, path: str, json_path: Optional[str] = None
    ) -> Return(keys=list, message=str):
        """Introspects a JSON object or array at a given path and returns its available keys or indices."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"keys": [], "message": f"File {path} not found."}

            with open(safe_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            target = data
            if json_path:
                target = self._get_nested(data, json_path.split("."))

            if isinstance(target, dict) or hasattr(target, "keys"):
                return {"keys": list(target.keys()), "message": "Success"}
            elif isinstance(target, list):
                return {"keys": list(range(len(target))), "message": "Success"}
            else:
                return {"keys": [], "message": "Target is not a collection."}
        except Exception as e:
            return {"keys": [], "message": f"Error: {str(e)}"}
