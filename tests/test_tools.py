import pytest
from typing import get_args, get_origin
import json

from ruamel.yaml import YAML
import tomllib


from deer.tools import ToolRegistry, Preset

_safe_yaml = YAML(typ="safe")


def build_registry() -> ToolRegistry:
    tr = ToolRegistry()
    tr.register(*[tool() for tool in Preset.ALL_TOOLS])
    return tr


def prepare_files(root, files, dirs):
    for rel_dir in dirs:
        (root / rel_dir).mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content)


@pytest.fixture
def jail_path(tmp_path):
    return tmp_path


@pytest.fixture
def tool_registry(jail_path):
    tr = build_registry()
    tr.set_jail(jail_path)
    return tr


def matches(expected, actual) -> bool:
    origin = get_origin(expected)
    if origin is list:
        (item_type,) = get_args(expected)
        return isinstance(actual, list) and all(matches(item_type, x) for x in actual)
    if isinstance(expected, type):
        return isinstance(actual, expected)
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and expected.keys() == actual.keys()
            and all(matches(expected[k], actual[k]) for k in expected)
        )
    return expected == actual


def check_paths(root, expected_paths):
    for rel in expected_paths:
        if rel.endswith("/"):
            assert (root / rel).is_dir(), f"Expected directory '{rel}' to exist"
        else:
            assert (root / rel).is_file(), f"Expected file '{rel}' to exist"


def check_json(root, expected_json):
    for rel, expected in expected_json.items():
        actual = json.loads((root / rel).read_text(encoding="utf-8"))
        assert actual == expected, f"{rel}: expected {expected}, got {actual}"


def check_yaml(root, expected_yaml):
    for rel, expected in expected_yaml.items():
        actual = _safe_yaml.load((root / rel).read_text(encoding="utf-8"))
        assert actual == expected, f"{rel}: expected {expected}, got {actual}"


def check_contains(root, expected_contains):
    for rel, fragments in expected_contains.items():
        text = (root / rel).read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in text, f"{rel}: '{fragment}' missing from:\n{text}"


def check_absent(root, expected_absent):
    for rel, fragments in expected_absent.items():
        text = (root / rel).read_text(encoding="utf-8")
        for fragment in fragments:
            assert (
                fragment not in text
            ), f"{rel}: '{fragment}' should be absent from:\n{text}"


def check_toml(root, expected_toml):
    for rel, expected in expected_toml.items():
        actual = tomllib.loads((root / rel).read_text(encoding="utf-8"))
        assert actual == expected, f"{rel}: expected {expected}, got {actual}"


def collect_cases():
    registry = build_registry()
    for name in registry.list_tools():
        tool = registry.get(name)
        if not tool.tests:
            yield pytest.param(
                name,
                None,
                id=f"{name}[no-tests]",
                marks=pytest.mark.skip(reason=f"{name} has no tests defined"),
            )
            continue
        for i, case in enumerate(tool.tests):
            yield pytest.param(name, case, id=f"{name}[{i}]")


@pytest.mark.parametrize("tool_name, case", collect_cases())
def test_tool(tool_registry, jail_path, tool_name, case):
    prepare_files(jail_path, case.files, case.dirs)

    tool = tool_registry.get(tool_name)

    if case.raises:
        with pytest.raises(case.raises):
            tool.method(**case.args)
        return

    result = tool.method(**case.args)
    assert matches(case.expected, result), f"Expected {case.expected}, got {result}"
    check_paths(jail_path, case.expected_paths)
    check_json(jail_path, case.expected_json)
    check_yaml(jail_path, case.expected_yaml)
    check_contains(jail_path, case.expected_contains)
    check_absent(jail_path, case.expected_absent)
