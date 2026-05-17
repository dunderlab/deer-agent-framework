import inspect
from types import NoneType, UnionType
from typing import Any, Callable, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from .base import Tool

_TOOL_METADATA_ATTR = "__nomos_tool_metadata__"
_MISSING = object()


def tool(
    *,
    name: str,
    description: str,
):
    """Mark an instance method as a deterministic tool."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        metadata = _build_tool_metadata(
            func=func,
            name=name,
            description=description,
        )
        setattr(
            func,
            _TOOL_METADATA_ATTR,
            metadata,
        )
        return staticmethod(func)

    return decorator


class MethodTool(Tool):
    """Adapter that exposes a decorated method as a Tool instance."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        # value_type: Any,
        params_type: Any,
        return_type: Any,
        method: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        # self.value_type = value_type
        self.params_type = params_type
        self.return_type = return_type
        self._method = method
        super().__init__()

    def run(self, value: Any, params: dict[str, Any] | None = None) -> Any:
        return self._method(params=params)


def is_tool_method(obj: Any) -> bool:
    return hasattr(obj, _TOOL_METADATA_ATTR)


def get_tool_metadata(obj: Any) -> dict[str, Any]:
    return getattr(obj, _TOOL_METADATA_ATTR)


def _build_tool_metadata(
    *,
    func: Callable[..., Any],
    name: str,
    description: str,
) -> dict[str, Any]:
    if not name or not name.strip():
        raise ValueError("Tool name cannot be empty.")

    if not description or not description.strip():
        raise ValueError("Tool description cannot be empty.")

    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    # value_type = _required_type_hint(
    #     func=func,
    #     signature=signature,
    #     type_hints=type_hints,
    #     parameter_name="value",
    # )
    params_type = _required_type_hint(
        func=func,
        signature=signature,
        type_hints=type_hints,
        parameter_name="params",
    )
    return_type = type_hints.get("return", _MISSING)

    if return_type is _MISSING:
        raise TypeError(
            f"Tool '{name}' must declare a return type annotation on "
            f"{func.__qualname__}."
        )

    full_description = _build_description(
        base_description=description.strip(),
        # value_type=value_type,
        params_type=params_type,
        return_type=return_type,
    )

    return {
        "name": name,
        "description": full_description,
        # "value_type": value_type,
        "params_type": params_type,
        "return_type": return_type,
    }


def _required_type_hint(
    *,
    func: Callable[..., Any],
    signature: inspect.Signature,
    type_hints: dict[str, Any],
    parameter_name: str,
) -> Any:
    if parameter_name not in signature.parameters:
        raise TypeError(
            f"Tool method {func.__qualname__} must declare a '{parameter_name}' "
            "parameter."
        )

    type_hint = type_hints.get(parameter_name, _MISSING)

    if type_hint is _MISSING:
        raise TypeError(
            f"Tool method {func.__qualname__} must type '{parameter_name}'."
        )

    return type_hint


def _build_description(
    *,
    base_description: str,
    # value_type: Any,
    params_type: Any,
    return_type: Any,
) -> str:
    return "\n".join(
        [
            base_description,
            # f"Input value: {_describe_type(value_type)}.",
            f"Input: {_describe_type(params_type)}.",
            f"Output: {_describe_type(return_type)}.",
        ]
    )


def _describe_type(type_hint: Any) -> str:
    if _is_typed_dict(type_hint):
        return _describe_structured_fields(type_hint.__annotations__)

    if _is_pydantic_model(type_hint):
        return _describe_structured_fields(
            {name: field.annotation for name, field in type_hint.model_fields.items()}
        )

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin is None:
        return _type_name(type_hint)

    if origin in (Union, UnionType):
        return " | ".join(_describe_type(arg) for arg in args)

    if origin is dict and len(args) == 2:
        return f"dict[{_describe_type(args[0])}, {_describe_type(args[1])}]"

    if origin in (list, tuple, set, frozenset):
        name = _type_name(origin)
        return f"{name}[{', '.join(_describe_type(arg) for arg in args)}]"

    if origin is Callable:
        return "Callable"

    return f"{_type_name(origin)}[{', '.join(_describe_type(arg) for arg in args)}]"


def _describe_structured_fields(fields: dict[str, Any]) -> str:
    field_descriptions = [
        f"'{field_name}' ({_describe_type(field_type)})"
        for field_name, field_type in fields.items()
    ]

    if not field_descriptions:
        return "object with no declared fields"

    return "object with fields " + ", ".join(field_descriptions)


def _type_name(type_hint: Any) -> str:
    if type_hint is None or type_hint is NoneType:
        return "None"

    if type_hint is Any:
        return "Any"

    return getattr(type_hint, "__name__", str(type_hint).replace("typing.", ""))


def _is_typed_dict(type_hint: Any) -> bool:
    return (
        isinstance(type_hint, type)
        and issubclass(type_hint, dict)
        and hasattr(type_hint, "__total__")
        and hasattr(type_hint, "__annotations__")
    )


def _is_pydantic_model(type_hint: Any) -> bool:
    return isinstance(type_hint, type) and issubclass(type_hint, BaseModel)
