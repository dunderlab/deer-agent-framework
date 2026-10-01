from dataclasses import dataclass
from typing import Any, Optional
from ruamel.yaml import YAML
import io

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case


@dataclass
class YAMLEditor(ToolProvider):
    """Provides surgical editing and introspection for YAML files, preserving comments and formatting."""

    def __post_init__(self):
        super().__post_init__()
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def _load(self, safe_path) -> Any:
        return self.yaml.load(safe_path.read_text(encoding="utf-8"))

    def _save(self, safe_path, data: Any) -> None:
        buffer = io.StringIO()
        self.yaml.dump(data, buffer)
        safe_path.write_text(buffer.getvalue(), encoding="utf-8")

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
                {"path": "a.yaml"},  # full file
                {"value": {"x": 1}, "message": "Success"},
                files={"a.yaml": "x: 1\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "x.y"},  # nested
                {"value": 1, "message": "Success"},
                files={"a.yaml": "x:\n  y: 1\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "items.1"},  # list index
                {"value": "b", "message": "Success"},
                files={"a.yaml": "items:\n  - a\n  - b\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "items.0.name"},  # list of mappings
                {"value": "n", "message": "Success"},
                files={"a.yaml": "items:\n  - name: n\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "n"},  # quoted string stays a string
                {"value": "1", "message": "Success"},
                files={"a.yaml": 'n: "1"\n'},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "n"},  # unquoted stays an int
                {"value": 1, "message": "Success"},
                files={"a.yaml": "n: 1\n"},
            ),
            Case(
                {
                    "path": "a.yaml",
                    "yaml_path": "x",
                },  # comments do not affect the value
                {"value": 1, "message": "Success"},
                files={"a.yaml": "# header\nx: 1  # inline\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "no.exists"},  # non-existent key
                {"value": None, "message": str},
                files={"a.yaml": "x: 1\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "items.5"},  # index out of range
                {"value": None, "message": str},
                files={"a.yaml": "items: []\n"},
            ),
            Case(
                {"path": "no_exists.yaml"},  # non-existent file
                {"value": None, "message": str},
            ),
            Case(
                {"path": "a.yaml"},  # invalid YAML
                {"value": None, "message": str},
                files={"a.yaml": "a: [1, 2"},
            ),
            Case({"path": "../outside.yaml"}, raises=Exception),  # jail
        ]
    )
    def read_yaml(
        self, path: str, yaml_path: Optional[str] = None
    ) -> Return(value=Any, message=str):
        """Navigates and extracts data from a YAML file using dot-notation, preserving original types and comments."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"value": None, "message": f"File {path} not found."}

            data = self._load(safe_path)

            if yaml_path:
                parts = yaml_path.split(".")
                value = self._get_nested(data, parts)
                return {"value": value, "message": "Success"}

            return {"value": data, "message": "Success"}
        except Exception as e:
            return {"value": None, "message": f"Error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.yaml", "yaml_path": "x", "value": 2},  # update existing key
                {"success": True, "message": str},
                files={"a.yaml": "x: 1\ny: 0\n"},
                expected_yaml={"a.yaml": {"x": 2, "y": 0}},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "z", "value": 3},  # add new key
                {"success": True, "message": str},
                files={"a.yaml": "x: 1\n"},
                expected_yaml={"a.yaml": {"x": 1, "z": 3}},
            ),
            Case(
                {
                    "path": "n.yaml",
                    "yaml_path": "a.b.c",
                    "value": 1,
                },  # new file + parents
                {"success": True, "message": str},
                expected_yaml={"n.yaml": {"a": {"b": {"c": 1}}}},
            ),
            Case(
                {"path": "d/e/n.yaml", "yaml_path": "k", "value": 1},  # create folders
                {"success": True, "message": str},
                expected_paths=["d/", "d/e/", "d/e/n.yaml"],
                expected_yaml={"d/e/n.yaml": {"k": 1}},
            ),
            Case(
                {"path": "n.yaml", "yaml_path": "items.0", "value": "a"},  # create list
                {"success": True, "message": str},
                expected_yaml={"n.yaml": {"items": ["a"]}},
            ),
            Case(
                {
                    "path": "a.yaml",
                    "yaml_path": "items.2",
                    "value": "c",
                },  # extend with null
                {"success": True, "message": str},
                files={"a.yaml": "items:\n  - a\n"},
                expected_yaml={"a.yaml": {"items": ["a", None, "c"]}},
            ),
            Case(
                {
                    "path": "a.yaml",
                    "yaml_path": "x",
                    "value": {"k": [1, 2]},
                },  # complex value
                {"success": True, "message": str},
                files={"a.yaml": "y: 0\n"},
                expected_yaml={"a.yaml": {"y": 0, "x": {"k": [1, 2]}}},
            ),
            Case(
                {
                    "path": "a.yaml",
                    "yaml_path": "x",
                    "value": "1",
                },  # string that looks like an int
                {"success": True, "message": str},
                files={"a.yaml": "y: 0\n"},
                expected_yaml={"a.yaml": {"y": 0, "x": "1"}},
            ),
            Case(
                {
                    "path": "a.yaml",
                    "yaml_path": "x",
                    "value": 2,
                },  # comments are preserved
                {"success": True, "message": str},
                files={"a.yaml": "# header\nx: 1  # keep\ny: 0\n"},
                expected_yaml={"a.yaml": {"x": 2, "y": 0}},
                expected_contains={"a.yaml": ["# header", "# keep"]},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "x", "value": 1},  # invalid YAML
                {"success": False, "message": str},
                files={"a.yaml": "a: [1, 2"},
            ),
            Case(
                {"path": "../outside.yaml", "yaml_path": "x", "value": 1},
                raises=Exception,
            ),  # jail
        ],
    )
    def update_yaml(
        self, path: str, yaml_path: str, value: Any
    ) -> Return(success=bool, message=str):
        """Performs a surgical upsert on a YAML path, automatically creating missing parents while preserving comments and structure."""
        safe_path = self.jailed_path(path)
        try:
            if safe_path.exists():
                data = self._load(safe_path)
            else:
                data = {}

            parts = yaml_path.split(".")
            self._set_nested(data, parts, value)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            self._save(safe_path, data)
            return {"success": True, "message": f"Updated {yaml_path} in {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.yaml", "yaml_path": "x"},  # top-level key
                {"success": True, "message": str},
                files={"a.yaml": "x: 1\ny: 2\n"},
                expected_yaml={"a.yaml": {"y": 2}},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "a.b"},  # nested key
                {"success": True, "message": str},
                files={"a.yaml": "a:\n  b: 1\n  c: 2\n"},
                expected_yaml={"a.yaml": {"a": {"c": 2}}},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "items.1"},  # list element
                {"success": True, "message": str},
                files={"a.yaml": "items:\n  - a\n  - b\n  - c\n"},
                expected_yaml={"a.yaml": {"items": ["a", "c"]}},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "x"},  # other comments are preserved
                {"success": True, "message": str},
                files={"a.yaml": "x: 1\ny: 2  # keep\n"},
                expected_yaml={"a.yaml": {"y": 2}},
                expected_contains={"a.yaml": ["# keep"]},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "no_exists"},  # non-existent key
                {"success": False, "message": str},
                files={"a.yaml": "x: 1\n"},
                expected_yaml={"a.yaml": {"x": 1}},
            ),  # file does not change
            Case(
                {"path": "a.yaml", "yaml_path": "items.9"},  # index out of range
                {"success": False, "message": str},
                files={"a.yaml": "items: []\n"},
            ),
            Case(
                {"path": "no_exists.yaml", "yaml_path": "x"},  # non-existent file
                {"success": False, "message": str},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "x"},  # invalid YAML
                {"success": False, "message": str},
                files={"a.yaml": "a: [1, 2"},
            ),
            Case(
                {"path": "../outside.yaml", "yaml_path": "x"}, raises=Exception
            ),  # jail
        ],
    )
    def remove_yaml_key(
        self, path: str, yaml_path: str
    ) -> Return(success=bool, message=str):
        """Surgically removes a mapping key or sequence index from a YAML file, maintaining file integrity and comments."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}

            data = self._load(safe_path)

            parts = yaml_path.split(".")
            parent_parts = parts[:-1]
            last_part = parts[-1]

            parent = data if not parent_parts else self._get_nested(data, parent_parts)

            if isinstance(parent, list):
                parent.pop(int(last_part))
            else:
                parent.pop(last_part)

            self._save(safe_path, data)
            return {"success": True, "message": f"Removed {yaml_path} from {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(
        tests=[
            Case(
                {"path": "a.yaml"},  # mapping root
                {"keys": ["x", "y"], "message": "Success"},
                files={"a.yaml": "x: 1\ny: 2\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "a"},  # nested
                {"keys": ["b"], "message": "Success"},
                files={"a.yaml": "a:\n  b: 1\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "items"},  # list: indices
                {"keys": [0, 1, 2], "message": "Success"},
                files={"a.yaml": "items:\n  - a\n  - b\n  - c\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "x"},  # not a collection
                {"keys": [], "message": "Target is not a collection."},
                files={"a.yaml": "x: 1\n"},
            ),
            Case(
                {"path": "a.yaml", "yaml_path": "no.exists"},  # non-existent path
                {"keys": [], "message": str},
                files={"a.yaml": "x: 1\n"},
            ),
            Case(
                {"path": "no_exists.yaml"},  # non-existent file
                {"keys": [], "message": str},
            ),
            Case({"path": "../outside.yaml"}, raises=Exception),  # jail
        ]
    )
    def list_yaml_keys(
        self, path: str, yaml_path: Optional[str] = None
    ) -> Return(keys=list, message=str):
        """Introspects a YAML collection at a given path and returns its keys or indices to aid in spatial awareness."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"keys": [], "message": f"File {path} not found."}

            data = self._load(safe_path)

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
