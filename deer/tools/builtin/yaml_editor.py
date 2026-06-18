from dataclasses import dataclass
from ruamel.yaml import YAML
from typing import Any, Optional, Union
from deer.tools import ToolProvider, tool
from deer.schema.io import Return
import io


@dataclass
class YAMLEditor(ToolProvider):
    """Provides surgical editing and introspection for YAML files, preserving comments and formatting."""

    def __post_init__(self):
        super().__post_init__()
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def _get_nested(self, data: Any, path_parts: list[str]) -> Any:
        current = data
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
    def read_yaml(
        self, path: str, yaml_path: Optional[str] = None
    ) -> Return(value=Any, message=str):
        """Navigates and extracts data from a YAML file using dot-notation, preserving original types and comments."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"value": None, "message": f"File {path} not found."}
            
            with open(safe_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            if yaml_path:
                parts = yaml_path.split(".")
                value = self._get_nested(data, parts)
                # Convert ruamel types to primitive if needed for Return schema, 
                # but Return(value=Any) should handle it.
                return {"value": value, "message": "Success"}

            return {"value": data, "message": "Success"}
        except Exception as e:
            return {"value": None, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def update_yaml(
        self, path: str, yaml_path: str, value: Any
    ) -> Return(success=bool, message=str):
        """Performs a surgical upsert on a YAML path, automatically creating missing parents while preserving comments and structure."""
        safe_path = self.jailed_path(path)
        try:
            if safe_path.exists():
                with open(safe_path, "r", encoding="utf-8") as f:
                    data = self.yaml.load(f)
            else:
                data = {}

            parts = yaml_path.split(".")
            self._set_nested(data, parts, value)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                self.yaml.dump(data, f)
            return {"success": True, "message": f"Updated {yaml_path} in {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def remove_yaml_key(
        self, path: str, yaml_path: str
    ) -> Return(success=bool, message=str):
        """Surgically removes a mapping key or sequence index from a YAML file, maintaining file integrity and comments."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}
            
            with open(safe_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            parts = yaml_path.split(".")
            parent_parts = parts[:-1]
            last_part = parts[-1]

            parent = data if not parent_parts else self._get_nested(data, parent_parts)

            if isinstance(parent, list):
                parent.pop(int(last_part))
            else:
                parent.pop(last_part)

            with open(safe_path, "w", encoding="utf-8") as f:
                self.yaml.dump(data, f)
            return {"success": True, "message": f"Removed {yaml_path} from {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool()
    def list_yaml_keys(
        self, path: str, yaml_path: Optional[str] = None
    ) -> Return(keys=list, message=str):
        """Introspects a YAML collection at a given path and returns its keys or indices to aid in spatial awareness."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"keys": [], "message": f"File {path} not found."}
            
            with open(safe_path, "r", encoding="utf-8") as f:
                data = self.yaml.load(f)

            target = data
            if yaml_path:
                target = self._get_nested(data, yaml_path.split("."))

            if isinstance(target, dict) or hasattr(target, "keys"):
                return {"keys": list(target.keys()), "message": "Success"}
            elif isinstance(target, list):
                return {"keys": list(range(len(target))), "message": "Success"}
            else:
                return {"keys": [], "message": "Target is not a collection."}
        except Exception as e:
            return {"keys": [], "message": f"Error: {str(e)}"}
