import ast
import math
from typing import Any, Mapping


class UnsafeLogicError(ValueError):
    """Raised when a logic expression contains unsupported or unsafe syntax."""


_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Call,
    ast.keyword,
    ast.Subscript,
    ast.Attribute,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.IfExp,
    ast.JoinedStr,
    ast.FormattedValue,
)


_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "str": str,
    "int": int,
    "float": float,
    "len": len,
}


_ALLOWED_NAMES = {
    "pi": math.pi,
}


def evaluate_logic(
    expression: str,
    *,
    input_value: Any,
    params: Mapping[str, Any],
    context: Mapping[str, Any],
) -> Any:
    """Evaluate a restricted Python expression.

    The expression must be a single expression, not statements.
    """

    tree = ast.parse(expression, mode="eval")
    _validate_ast(tree)

    scope = {
        **_ALLOWED_NAMES,
        **_ALLOWED_FUNCTIONS,
        "input": input_value,
        "params": dict(params),
        "context": dict(context),
    }

    compiled = compile(tree, filename="<step.logic>", mode="eval")
    return eval(compiled, {"__builtins__": {}}, scope)


def _validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeLogicError(
                f"Unsupported syntax in logic expression: {type(node).__name__}"
            )

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise UnsafeLogicError(
                    "Only direct calls to allowed functions are supported."
                )

            if node.func.id not in _ALLOWED_FUNCTIONS:
                raise UnsafeLogicError(f"Unsupported function call: {node.func.id}")

        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise UnsafeLogicError(
                    "Private attributes are not allowed in logic expressions."
                )

        if isinstance(node, ast.Name):
            allowed_names = (
                set(_ALLOWED_NAMES)
                | set(_ALLOWED_FUNCTIONS)
                | {
                    "input",
                    "params",
                    "context",
                }
            )

            if node.id not in allowed_names:
                raise UnsafeLogicError(f"Unknown name in logic expression: {node.id}")
