from dataclasses import dataclass
from typing import Any, Optional
import json

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case


@dataclass
class JSONEditor(ToolProvider):

    def _load(self, safe_path) -> Any:
        return json.loads(safe_path.read_text(encoding="utf-8"))

    def _save(self, safe_path, data: Any) -> None:
        text = json.dumps(data, indent=2, ensure_ascii=False)
        safe_path.write_text(text + "\n", encoding="utf-8")

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

    @tool(
        tests=[
            Case(
                {"path": "a.json"},  # full file
                {"value": {"x": 1}, "message": "Success"},
                files={"a.json": '{"x": 1}'},
            ),
            Case(
                {"path": "a.json", "json_path": "x.y"},  # nested
                {"value": 1, "message": "Success"},
                files={"a.json": '{"x": {"y": 1}}'},
            ),
            Case(
                {"path": "a.json", "json_path": "items.1"},  # list index
                {"value": "b", "message": "Success"},
                files={"a.json": '{"items": ["a", "b"]}'},
            ),
            Case(
                {"path": "a.json", "json_path": "items.0.name"},  # list of objects
                {"value": "n", "message": "Success"},
                files={"a.json": '{"items": [{"name": "n"}]}'},
            ),
            Case(
                {"path": "a.json", "json_path": "no.existe"},  # non-existent key
                {"value": None, "message": str},
                files={"a.json": '{"x": 1}'},
            ),
            Case(
                {"path": "a.json", "json_path": "items.5"},  # index out of range
                {"value": None, "message": str},
                files={"a.json": '{"items": []}'},
            ),
            Case(
                {"path": "no_existe.json"},  # non-existent file
                {"value": None, "message": str},
            ),
            Case(
                {"path": "a.json"},  # invalid JSON
                {"value": None, "message": str},
                files={"a.json": "{no es json"},
            ),
            Case({"path": "../fuera.json"}, raises=Exception),
        ]
    )
    def read_json(
        self, path: str, json_path: Optional[str] = None
    ) -> Return(value=Any, message=str):
        """Navigates and extracts data from a JSON file using dot-notation."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"value": None, "message": f"File {path} not found."}

            data = self._load(safe_path)
            value = self._get_nested(data, json_path.split(".")) if json_path else data
            return {"value": value, "message": "Success"}
        except Exception as e:
            return {"value": None, "message": f"Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {
                    "path": "a.json",
                    "json_path": "x",
                    "value": 2,
                },  # update existing key
                {"success": True, "message": str},
                files={"a.json": '{"x": 1, "y": 0}'},
                expected_json={"a.json": {"x": 2, "y": 0}},
            ),
            Case(
                {"path": "a.json", "json_path": "z", "value": 3},  # add new key
                {"success": True, "message": str},
                files={"a.json": '{"x": 1}'},
                expected_json={"a.json": {"x": 1, "z": 3}},
            ),
            Case(
                {
                    "path": "n.json",
                    "json_path": "a.b.c",
                    "value": 1,
                },  # new file + parents
                {"success": True, "message": str},
                expected_json={"n.json": {"a": {"b": {"c": 1}}}},
            ),
            Case(
                {"path": "d/e/n.json", "json_path": "k", "value": 1},  # create folders
                {"success": True, "message": str},
                expected_paths=["d/", "d/e/", "d/e/n.json"],
                expected_json={"d/e/n.json": {"k": 1}},
            ),
            Case(
                {"path": "n.json", "json_path": "items.0", "value": "a"},  # create list
                {"success": True, "message": str},
                expected_json={"n.json": {"items": ["a"]}},
            ),
            Case(
                {
                    "path": "a.json",
                    "json_path": "items.2",
                    "value": "c",
                },  # extend with null
                {"success": True, "message": str},
                files={"a.json": '{"items": ["a"]}'},
                expected_json={"a.json": {"items": ["a", None, "c"]}},
            ),
            Case(
                {
                    "path": "a.json",
                    "json_path": "x",
                    "value": {"k": [1, 2]},
                },  # complex value
                {"success": True, "message": str},
                files={"a.json": "{}"},
                expected_json={"a.json": {"x": {"k": [1, 2]}}},
            ),
            Case(
                {
                    "path": "a.json",
                    "json_path": "x",
                    "value": 1,
                },  # invalid JSON: do not touch
                {"success": False, "message": str},
                files={"a.json": "{roto"},
            ),
        ],
    )
    def update_json(
        self, path: str, json_path: str, value: Any
    ) -> Return(success=bool, message=str):
        """Upserts a value at a dot-notation path in a JSON file, creating the file and any missing parent objects or lists. Fails if the existing file is not valid JSON."""
        safe_path = self.jailed_path(path)
        try:
            if safe_path.exists():
                data = self._load(safe_path)
            else:
                data = {}

            parts = json_path.split(".")
            self._set_nested(data, parts, value)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            self._save(safe_path, data)

            return {"success": True, "message": f"Updated {json_path} in {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.json", "json_path": "x"},  # top-level key
                {"success": True, "message": str},
                files={"a.json": '{"x": 1, "y": 2}'},
                expected_json={"a.json": {"y": 2}},
            ),
            Case(
                {"path": "a.json", "json_path": "a.b"},  # nested key
                {"success": True, "message": str},
                files={"a.json": '{"a": {"b": 1, "c": 2}}'},
                expected_json={"a.json": {"a": {"c": 2}}},
            ),
            Case(
                {"path": "a.json", "json_path": "items.1"},  # list element
                {"success": True, "message": str},
                files={"a.json": '{"items": ["a", "b", "c"]}'},
                expected_json={"a.json": {"items": ["a", "c"]}},
            ),
            Case(
                {"path": "a.json", "json_path": "no_existe"},  # non-existent key
                {"success": False, "message": str},
                files={"a.json": '{"x": 1}'},
                expected_json={"a.json": {"x": 1}},
            ),  # file does not change
            Case(
                {"path": "a.json", "json_path": "items.9"},  # índice fuera de rango
                {"success": False, "message": str},
                files={"a.json": '{"items": []}'},
            ),
            Case(
                {"path": "no_existe.json", "json_path": "x"},  # archivo inexistente
                {"success": False, "message": str},
            ),
            Case(
                {"path": "a.json", "json_path": "x"},
                {"success": False, "message": str},
                files={"a.json": "{roto"},
            ),
        ],
    )
    def remove_json_key(
        self, path: str, json_path: str
    ) -> Return(success=bool, message=str):
        """Removes a key or array element at a dot-notation path from a JSON file. Fails if the file or the path does not exist."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}

            data = self._load(safe_path)

            parts = json_path.split(".")
            parent_parts = parts[:-1]
            last_part = parts[-1]

            parent = data if not parent_parts else self._get_nested(data, parent_parts)

            if isinstance(parent, list):
                parent.pop(int(last_part))
            else:
                parent.pop(last_part)

            self._save(safe_path, data)

            return {"success": True, "message": f"Removed {json_path} from {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(
        tests=[
            Case(
                {"path": "a.json"},  # object root
                {"keys": ["x", "y"], "message": "Success"},
                files={"a.json": '{"x": 1, "y": 2}'},
            ),
            Case(
                {"path": "a.json", "json_path": "a"},  # nested
                {"keys": ["b"], "message": "Success"},
                files={"a.json": '{"a": {"b": 1}}'},
            ),
            Case(
                {"path": "a.json", "json_path": "items"},  # list: indices
                {"keys": [0, 1, 2], "message": "Success"},
                files={"a.json": '{"items": ["a", "b", "c"]}'},
            ),
            Case(
                {"path": "a.json", "json_path": "x"},  # not a collection
                {"keys": [], "message": "Target is not a collection."},
                files={"a.json": '{"x": 1}'},
            ),
            Case(
                {"path": "a.json", "json_path": "no.existe"},  # non-existent path
                {"keys": [], "message": str},
                files={"a.json": "{}"},
            ),
            Case(
                {"path": "no_existe.json"},  # archivo inexistente
                {"keys": [], "message": str},
            ),
        ]
    )
    def list_json_keys(
        self, path: str, json_path: Optional[str] = None
    ) -> Return(keys=list, message=str):
        """Introspects a JSON object or array at a given path and returns its available keys or indices."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"keys": [], "message": f"File {path} not found."}

            data = self._load(safe_path)

            target = data
            if json_path:
                target = self._get_nested(data, json_path.split("."))

            if isinstance(target, dict):
                return {"keys": list(target.keys()), "message": "Success"}
            elif isinstance(target, list):
                return {"keys": list(range(len(target))), "message": "Success"}
            else:
                return {"keys": [], "message": "Target is not a collection."}
        except Exception as e:
            return {"keys": [], "message": f"Error: {str(e)}"}
