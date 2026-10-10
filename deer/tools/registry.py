from typing import Any, get_origin, get_args, Union, Iterable, Literal
from pydantic import BaseModel

from .base import Tool
from .decorators import MethodTool, get_tool_metadata, is_tool_method
from .schemas import Return


class ToolRegistry:
    def __init__(self, tools=None, jail_path=None) -> None:
        self.tools: dict[str, Tool] = {}
        self._providers: list = []

        if tools:
            self.register(*[tool() for tool in tools])

        if jail_path:
            self.jail_path = jail_path
            self.set_jail(jail_path)

    def register(self, *provider_tools: list):
        for tool in provider_tools:
            if isinstance(tool, Tool):
                self._register_tool(tool)
            else:
                self._register_collection(tool)

    def _register_tool(self, tool: Tool) -> None:
        if not tool.name or not tool.name.strip():
            raise ValueError("Tool name cannot be empty.")

        if tool.name in self.tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")

        self.tools[tool.name] = tool

    def _register_collection(self, provider: Any) -> None:
        self._providers.append(provider)
        for attr_name in dir(provider):

            if attr_name == "jail":
                continue

            attr = getattr(provider, attr_name, None)
            if attr is None:
                continue

            if not is_tool_method(attr):
                continue

            metadata = get_tool_metadata(attr)

            self.register(
                MethodTool(
                    name=metadata["name"],
                    description=metadata["description"],
                    # full_description=metadata["full_description"],
                    modifies_state=metadata["modifies_state"],
                    params_type=metadata["params_type"],
                    return_type=metadata["return_type"],
                    tests=metadata.get("tests", []),
                    method=attr,
                )
            )

    def get(self, name: str) -> Tool:
        if not name or not name.strip():
            raise KeyError("Tool name cannot be empty.")

        if name not in self.tools:
            raise KeyError(f"Tool not found: {name}")

        return self.tools[name]

    def has(self, name: str | None) -> bool:
        if not name:
            return False

        return name in self.tools

    def list_tools(self) -> Iterable[str]:
        return self.tools.keys()

    def providers(self):
        return self._providers

    def set_jail(self, jail_path):
        self.jail_path = jail_path
        for provider in self._providers:
            provider.jail = jail_path

    def describe(
        self, state_filter: Literal["READ_ONLY", "MODIFIES_STATE", "BOTH"] = "BOTH"
    ) -> str:

        if not self.tools:
            return "- No tools are available."

        lines = []

        for tool in self.tools.values():

            if state_filter == "READ_ONLY" and tool.modifies_state:
                continue  # Skip tools that modify state

            if state_filter == "MODIFIES_STATE" and not tool.modifies_state:
                continue  # Skip tools that are read-only

            params_list = []
            for name, p_type in tool.params_type.items():
                clean_type = self.stringify_type(p_type)
                params_list.append(f"{name}: {clean_type}")
            params_str = ", ".join(params_list)

            return_type = {
                key: self.stringify_type(value)
                for key, value in tool.return_type.items()
            }

            state_flag = "MODIFIES STATE" if tool.modifies_state else "READ ONLY"

            lines.append(
                f"- {tool.name}({params_str}) -> {return_type} | {state_flag} | {tool.description.replace('\n', ' ')}"
            )

        return "\n".join(lines)

    def stringify_type(self, t: Any) -> str:
        """
        Recursively converts a Python type (including nested Generics)
        into a clean, human-readable string for the LLM.
        """
        # 1. Handle Basic Types (str, int, float, bool, etc.)
        if hasattr(t, "__name__") and not hasattr(t, "__origin__"):
            return t.__name__

        # 2. Handle Pydantic Models
        if isinstance(t, type) and issubclass(t, BaseModel):
            return t.__name__

        # 3. Handle Generic Aliases (list[str], dict[str, int], Optional[...], etc.)
        origin = get_origin(t)
        if origin is not None:
            args = get_args(t)
            # Clean the origin name (e.g., 'list' instead of 'typing.List')
            origin_name = getattr(origin, "__name__", str(origin))

            # Special case for Optional/Union
            if origin is Union:
                # If it's Optional[T], it's actually Union[T, NoneType]
                if len(args) == 2 and type(None) in args:
                    # Find the non-None type
                    actual_type = args[0] if args[1] is type(None) else args[1]
                    return f"Optional[{self.stringify_type(actual_type)}]"

                # Standard Union: Union[str, int]
                return f"Union[{', '.join(self.stringify_type(a) for a in args)}]"

            # Standard Generics: list[str], dict[str, int]
            args_str = ", ".join(self.stringify_type(a) for a in args)
            return f"{origin_name}[{args_str}]"

        # 4. Fallback for everything else
        return str(t)


class EchoTool(Tool):
    name = "echo"
    description = "Returns params['echo'] when provided; otherwise returns the input value unchanged."
    modifies_state = False

    def run(self, params: dict[str, Any] | None = None) -> Return(echo=dict):
        params = params or {}
        return params


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(EchoTool())
    return reg
