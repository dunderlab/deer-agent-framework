import pytest
from deer.tools import ToolRegistry, Preset


def build_registry() -> ToolRegistry:
    tr = ToolRegistry()
    tr.register(*[tool() for tool in Preset.ALL_TOOLS])
    return tr


def prepare_files(root, files):
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
    if isinstance(expected, type):
        return isinstance(actual, expected)
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and expected.keys() == actual.keys()
            and all(matches(expected[k], actual[k]) for k in expected)
        )
    return expected == actual


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
    prepare_files(jail_path, case.files)

    tool = tool_registry.get(tool_name)
    result = tool.method(**case.args)
    assert matches(case.expected, result), f"Expected {case.expected}, got {result}"
