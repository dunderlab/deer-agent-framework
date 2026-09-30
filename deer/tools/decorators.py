from typing import get_type_hints, Any, Callable, Optional
from dataclasses import dataclass

from pydantic import BaseModel

from .base import Tool

from .schemas import Case

_TOOL_METADATA_ATTR = "__deer_tool_metadata__"
_MISSING = object()


def tool(
    *,
    modifies_state: bool = False,
    tests: Optional[list[Case]] = [],
):
    """Mark an instance method as a deterministic tool."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        assert func.__doc__, f"Tool '{func.__name__}' must have a docstring annotation."

        metadata = _build_tool_metadata(
            func=func,
            name=func.__name__,
            description=func.__doc__,
            modifies_state=modifies_state,
            tests=tests,
        )
        setattr(
            func,
            _TOOL_METADATA_ATTR,
            metadata,
        )
        return func
        # return staticmethod(func)

    return decorator


@dataclass(slots=True)
class MethodTool(Tool):
    """Adapter that exposes a decorated method as a Tool instance."""

    name: str
    description: str
    params_type: Any
    return_type: Any
    method: Callable[..., Any]
    modifies_state: bool
    tests: list[Case]

    def run(
        self,
        params: dict[str, Any] | None = None,
    ) -> Any:

        # 1. Strict Input Validation
        validated_params = self.validate_input(params)
        # 2. Execution
        result = self.method(**(validated_params or {}))
        # 3. Strict Output Validation
        return self.validate_output(result)

        # return self.method(**params)


def is_tool_method(obj: Any) -> bool:
    return hasattr(obj, _TOOL_METADATA_ATTR) and (
        not obj.__self__.tools or obj.__name__ in obj.__self__.tools
    )


def get_tool_metadata(obj: Any) -> dict[str, Any]:
    return getattr(obj, _TOOL_METADATA_ATTR)


def _build_tool_metadata(
    *,
    func: Callable[..., Any],
    name: str,
    description: str,
    modifies_state: bool,
    tests: list = [],
) -> dict[str, Any]:
    if not name or not name.strip():
        raise ValueError("Tool name cannot be empty.")

    if not description or not description.strip():
        raise ValueError("Tool description cannot be empty.")

    # signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    return_type = type_hints.pop("return")
    params_type = type_hints

    if issubclass(return_type, BaseModel):
        return_type = {
            name: field.annotation for name, field in return_type.model_fields.items()
        }

    if return_type is _MISSING:
        raise TypeError(
            f"Tool '{name}' must declare a return type annotation on "
            f"{func.__qualname__}."
        )

    # full_description = _build_description(
    #     base_description=description.strip(),
    #     params_type=params_type,
    #     return_type=return_type,
    # )

    return {
        "name": name,
        "description": description.strip(),
        # "full_description": full_description,
        "modifies_state": modifies_state,
        "tests": tests,
        "params_type": params_type,
        "return_type": return_type,
    }


#
# def _build_description(
#     *,
#     base_description: str,
#     params_type: Any,
#     return_type: Any,
# ) -> str:
#
#     return "\n".join(
#         [
#             base_description,
#             f"Parameters: {params_type}.",
#             f"Return: {return_type}.",
#         ]
#     )
