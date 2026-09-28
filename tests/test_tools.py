import pytest
from deer.tools import ToolProvider, ToolRegistry, tool, Return
from dataclasses import dataclass


@pytest.fixture
def tool_registry():

    @dataclass
    class ToolExample(ToolProvider):

        @tool(modifies_state=False)
        def boolean_tool(self, arg1: str, arg2: int) -> Return(result=bool):
            """This is the `boolean_tool` description."""
            return {
                "result": True,
            }

        @tool(modifies_state=True)
        def boolean_tool_mod(self, arg1: str, arg2: int) -> Return(result=bool):
            """This is the `boolean_tool_mod` description."""
            return {
                "result": True,
            }

    tr = ToolRegistry()
    tr.register(*[tool() for tool in [ToolExample]])
    return tr


def test_description(tool_registry):

    tool_registry.describe()

    pass
