from typing import Any, Dict, Iterable

from .base import Tool
from .decorators import MethodTool, get_tool_metadata, is_tool_method
from deer.schema.io import Return


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, *provider_tools: list):
        for tool in provider_tools:
            if isinstance(tool, Tool):
                self._register_tool(tool)
            else:
                self._register_collection(tool)

    def _register_tool(self, tool: Tool) -> None:
        if not tool.name or not tool.name.strip():
            raise ValueError("Tool name cannot be empty.")

        self._tools[tool.name] = tool

    def _register_collection(self, provider: Any) -> None:
        for attr_name in dir(provider):
            attr = getattr(provider, attr_name)

            if not is_tool_method(attr):
                continue

            metadata = get_tool_metadata(attr)

            self.register(
                MethodTool(
                    name=metadata["name"],
                    description=metadata["description"],
                    full_description=metadata["full_description"],
                    modifies_state=metadata["modifies_state"],
                    params_type=metadata["params_type"],
                    return_type=metadata["return_type"],
                    method=attr,
                )
            )

    def get(self, name: str) -> Tool:
        if not name or not name.strip():
            raise KeyError("Tool name cannot be empty.")

        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        return self._tools[name]

    def has(self, name: str | None) -> bool:
        if not name:
            return False

        return name in self._tools

    def list_tools(self) -> Iterable[str]:
        return self._tools.keys()

    def describe(self, include_state_modifying=True, markdown=False) -> str:
        if not self._tools:
            return "- No tools are available."

        lines = []

        for tool in self._tools.values():

            if not include_state_modifying and tool.modifies_state:
                continue

            if markdown:
                lines.append(f" - `{tool.name}`: *{tool.description.split('\n')[0]}*")
            else:
                lines.append(
                    f"- {tool.name}: {tool.full_description.replace("\n", "\n  ")}"
                )

        return "\n".join(lines)


class EchoTool(Tool):
    name = "echo"
    description = "Returns params['echo'] when provided; otherwise returns the input value unchanged."
    modifies_state = False

    def run(self, params: dict[str, Any] | None = None) -> Return(echo={}):
        params = params or {}
        return params


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(EchoTool())
    return reg
