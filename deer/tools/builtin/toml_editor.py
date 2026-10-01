from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import tomlkit

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Case, Return


@dataclass
class TOMLEditor(ToolProvider):
    """Provides surgical editing and introspection for TOML files, preserving comments and formatting."""

    def _load(self, safe_path: Path) -> Any:
        return tomlkit.parse(safe_path.read_text(encoding="utf-8"))

    def _save(self, safe_path: Path, data: Any) -> None:
        # Serialize first: the file is only touched once the text exists.
        text = tomlkit.dumps(data)
        safe_path.write_text(text, encoding="utf-8")

    @staticmethod
    def _plain(value: Any) -> Any:
        """Converts tomlkit items into plain Python types."""
        return value.unwrap() if hasattr(value, "unwrap") else value

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
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = tomlkit.table()
            current = current[part]

        current[path_parts[-1]] = value

    @tool(
        tests=[
            Case(
                {"path": "a.toml"},  # full file
                {"value": {"x": 1}, "message": "Success"},
                files={"a.toml": "x = 1\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "a.b"},  # nested
                {"value": 1, "message": "Success"},
                files={"a.toml": "[a]\nb = 1\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "a"},  # whole table as plain dict
                {"value": {"b": 1}, "message": "Success"},
                files={"a.toml": "[a]\nb = 1\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "items.1"},  # array index
                {"value": "b", "message": "Success"},
                files={"a.toml": 'items = ["a", "b"]\n'},
            ),
            Case(
                {"path": "a.toml", "toml_path": "items.0.name"},  # array of tables
                {"value": "n", "message": "Success"},
                files={"a.toml": '[[items]]\nname = "n"\n'},
            ),
            Case(
                {"path": "a.toml", "toml_path": "n"},  # quoted string stays a string
                {"value": "1", "message": "Success"},
                files={"a.toml": 'n = "1"\n'},
            ),
            Case(
                {"path": "a.toml", "toml_path": "n"},  # unquoted stays an int
                {"value": 1, "message": "Success"},
                files={"a.toml": "n = 1\n"},
            ),
            Case(
                {
                    "path": "a.toml",
                    "toml_path": "x",
                },  # comments do not affect the value
                {"value": 1, "message": "Success"},
                files={"a.toml": "# header\nx = 1  # inline\n"},
            ),
            Case(
                {"path": "a.toml"},  # empty file
                {"value": {}, "message": "Success"},
                files={"a.toml": ""},
            ),
            Case(
                {"path": "a.toml", "toml_path": "no.exists"},  # non-existent key
                {"value": None, "message": str},
                files={"a.toml": "x = 1\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "items.5"},  # index out of range
                {"value": None, "message": str},
                files={"a.toml": "items = []\n"},
            ),
            Case(
                {"path": "no_exists.toml"},  # non-existent file
                {"value": None, "message": str},
            ),
            Case(
                {"path": "a.toml"},  # invalid TOML
                {"value": None, "message": str},
                files={"a.toml": "x = "},
            ),
            Case({"path": "../outside.toml"}, raises=Exception),  # jail
        ]
    )
    def read_toml(
        self, path: str, toml_path: Optional[str] = None
    ) -> Return(value=Any, message=str):
        """Navigates and extracts data from a TOML file using dot-notation. Array elements are addressed by index (e.g. 'items.0.name')."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"value": None, "message": f"File {path} not found."}

            data = self._load(safe_path)
            value = self._get_nested(data, toml_path.split(".")) if toml_path else data
            return {"value": self._plain(value), "message": "Success"}
        except Exception as e:
            return {"value": None, "message": f"Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.toml", "toml_path": "x", "value": 2},  # update existing key
                {"success": True, "message": str},
                files={"a.toml": "x = 1\ny = 0\n"},
                expected_toml={"a.toml": {"x": 2, "y": 0}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "z", "value": 3},  # add new key
                {"success": True, "message": str},
                files={"a.toml": "x = 1\n"},
                expected_toml={"a.toml": {"x": 1, "z": 3}},
            ),
            Case(
                {
                    "path": "n.toml",
                    "toml_path": "a.b.c",
                    "value": 1,
                },  # new file + tables
                {"success": True, "message": str},
                expected_toml={"n.toml": {"a": {"b": {"c": 1}}}},
            ),
            Case(
                {"path": "d/e/n.toml", "toml_path": "k", "value": 1},  # create folders
                {"success": True, "message": str},
                expected_paths=["d/", "d/e/", "d/e/n.toml"],
                expected_toml={"d/e/n.toml": {"k": 1}},
            ),
            Case(
                {
                    "path": "a.toml",
                    "toml_path": "a.c",
                    "value": 2,
                },  # add to existing table
                {"success": True, "message": str},
                files={"a.toml": "[a]\nb = 1\n"},
                expected_toml={"a.toml": {"a": {"b": 1, "c": 2}}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x", "value": "hi"},  # string value
                {"success": True, "message": str},
                files={"a.toml": "y = 0\n"},
                expected_toml={"a.toml": {"y": 0, "x": "hi"}},
            ),
            Case(
                {
                    "path": "a.toml",
                    "toml_path": "x",
                    "value": "1",
                },  # string that looks like an int
                {"success": True, "message": str},
                files={"a.toml": "y = 0\n"},
                expected_toml={"a.toml": {"y": 0, "x": "1"}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x", "value": [1, 2, 3]},  # list value
                {"success": True, "message": str},
                files={"a.toml": "y = 0\n"},
                expected_toml={"a.toml": {"y": 0, "x": [1, 2, 3]}},
            ),
            Case(
                {
                    "path": "a.toml",
                    "toml_path": "x",
                    "value": {"k": [1, 2]},
                },  # complex value
                {"success": True, "message": str},
                files={"a.toml": "y = 0\n"},
                expected_toml={"a.toml": {"y": 0, "x": {"k": [1, 2]}}},
            ),
            Case(
                {
                    "path": "a.toml",
                    "toml_path": "x",
                    "value": 2,
                },  # comments are preserved
                {"success": True, "message": str},
                files={"a.toml": "# header\nx = 1\ny = 0  # keep\n"},
                expected_toml={"a.toml": {"x": 2, "y": 0}},
                expected_contains={"a.toml": ["# header", "# keep"]},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x", "value": 1},  # empty file
                {"success": True, "message": str},
                files={"a.toml": ""},
                expected_toml={"a.toml": {"x": 1}},
            ),
            Case(
                {
                    "path": "a.toml",
                    "toml_path": "a.b",
                    "value": 1,
                },  # a scalar is in the way
                {"success": False, "message": str},
                files={"a.toml": "a = 1\n"},
                expected_toml={"a.toml": {"a": 1}},  # file does not change
            ),
            Case(
                {"path": "a.toml", "toml_path": "x", "value": None},  # TOML has no null
                {"success": False, "message": str},
                files={"a.toml": "y = 0\n"},
                expected_toml={"a.toml": {"y": 0}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x", "value": 1},  # invalid TOML
                {"success": False, "message": str},
                files={"a.toml": "x = "},
            ),
            Case(
                {"path": "../outside.toml", "toml_path": "x", "value": 1},  # jail
                raises=Exception,
            ),
        ],
    )
    def update_toml(
        self, path: str, toml_path: str, value: Any
    ) -> Return(success=bool, message=str):
        """Updates or adds a value at a dot-notation path in a TOML file, creating the file and any missing tables, and preserving comments. Cannot create or traverse arrays. Fails if the existing file is not valid TOML. TOML has no null value."""
        safe_path = self.jailed_path(path)
        try:
            data = self._load(safe_path) if safe_path.exists() else tomlkit.document()

            self._set_nested(data, toml_path.split("."), value)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            self._save(safe_path, data)

            return {"success": True, "message": f"Updated {toml_path} in {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.toml", "toml_path": "x"},  # top-level key
                {"success": True, "message": str},
                files={"a.toml": "x = 1\ny = 2\n"},
                expected_toml={"a.toml": {"y": 2}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "a.b"},  # nested key
                {"success": True, "message": str},
                files={"a.toml": "[a]\nb = 1\nc = 2\n"},
                expected_toml={"a.toml": {"a": {"c": 2}}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "a"},  # whole table
                {"success": True, "message": str},
                files={"a.toml": "x = 1\n\n[a]\nb = 1\n"},
                expected_toml={"a.toml": {"x": 1}},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x"},  # other comments are preserved
                {"success": True, "message": str},
                files={"a.toml": "# header\nx = 1\ny = 2  # keep\n"},
                expected_toml={"a.toml": {"y": 2}},
                expected_contains={"a.toml": ["# header", "# keep"]},
            ),
            Case(
                {"path": "a.toml", "toml_path": "no_exists"},  # non-existent key
                {"success": False, "message": str},
                files={"a.toml": "x = 1\n"},
                expected_toml={"a.toml": {"x": 1}},  # file does not change
            ),
            Case(
                {"path": "a.toml", "toml_path": "no.exists"},  # non-existent parent
                {"success": False, "message": str},
                files={"a.toml": "x = 1\n"},
                expected_toml={"a.toml": {"x": 1}},
            ),
            Case(
                {"path": "no_exists.toml", "toml_path": "x"},  # non-existent file
                {"success": False, "message": str},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x"},  # invalid TOML
                {"success": False, "message": str},
                files={"a.toml": "x = "},
            ),
            Case(
                {"path": "../outside.toml", "toml_path": "x"},  # jail
                raises=Exception,
            ),
        ],
    )
    def remove_toml_key(
        self, path: str, toml_path: str
    ) -> Return(success=bool, message=str):
        """Removes a key (or a whole table) at a dot-notation path from a TOML file, preserving the rest of the file and its comments. Fails if the file or the key does not exist."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}

            data = self._load(safe_path)

            parts = toml_path.split(".")
            parent = data if len(parts) == 1 else self._get_nested(data, parts[:-1])

            if parts[-1] not in parent:
                return {"success": False, "message": f"Key {toml_path} not found."}

            del parent[parts[-1]]

            self._save(safe_path, data)
            return {"success": True, "message": f"Removed {toml_path} from {path}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    @tool(
        tests=[
            Case(
                {"path": "a.toml"},  # root
                {"keys": ["x", "y"], "message": "Success"},
                files={"a.toml": "x = 1\ny = 2\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "a"},  # nested
                {"keys": ["b"], "message": "Success"},
                files={"a.toml": "[a]\nb = 1\n"},
            ),
            Case(
                {"path": "a.toml"},  # empty file
                {"keys": [], "message": "Success"},
                files={"a.toml": ""},
            ),
            Case(
                {"path": "a.toml", "toml_path": "x"},  # not a table
                {"keys": [], "message": "Target is not a table."},
                files={"a.toml": "x = 1\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "items"},  # arrays are not tables
                {"keys": [], "message": "Target is not a table."},
                files={"a.toml": "items = [1, 2]\n"},
            ),
            Case(
                {"path": "a.toml", "toml_path": "no.exists"},  # non-existent path
                {"keys": [], "message": str},
                files={"a.toml": "x = 1\n"},
            ),
            Case(
                {"path": "no_exists.toml"},  # non-existent file
                {"keys": [], "message": str},
            ),
            Case(
                {"path": "a.toml"},  # invalid TOML
                {"keys": [], "message": str},
                files={"a.toml": "x = "},
            ),
            Case({"path": "../outside.toml"}, raises=Exception),  # jail
        ]
    )
    def list_toml_keys(
        self, path: str, toml_path: Optional[str] = None
    ) -> Return(keys=list, message=str):
        """Returns the keys of the TOML table at a dot-notation path (or of the root if no path is given). Fails if the path does not point to a table."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"keys": [], "message": f"File {path} not found."}

            data = self._load(safe_path)
            target = self._get_nested(data, toml_path.split(".")) if toml_path else data

            if isinstance(target, dict):
                return {"keys": list(target.keys()), "message": "Success"}
            return {"keys": [], "message": "Target is not a table."}
        except Exception as e:
            return {"keys": [], "message": f"Error: {e}"}
