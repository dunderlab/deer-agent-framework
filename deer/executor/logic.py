import ast
import math
from typing import Any, Dict, Mapping


class UnsafeLogicError(ValueError):
    """Raised when the code contains disallowed or dangerous syntax."""


# Allowed nodes to permit mathematical logic, strings, and basic assignments
_ALLOWED_NODE_TYPES = (
    ast.Module,
    ast.Assign,
    ast.Expr,
    ast.Store,
    ast.Load,
    ast.Name,
    ast.Constant,
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

_SAFE_GLOBALS = {
    "__builtins__": {},
    "pi": math.pi,
    "e": math.e,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "pow": pow,
    "sum": sum,
    "sqrt": math.sqrt,
    "log": math.log,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "str": str,
    "int": int,
    "float": float,
    "len": len,
    "bool": bool,
    "list": list,
    "dict": dict,
    "enumerate": enumerate,
    "zip": zip,
    "range": range,
}


def _is_safe_variable_name(name: str) -> bool:
    return name.isidentifier() and not name.startswith("_")


def evaluate_logic(
    logic_code: str,
    *,
    input_value: Any,
    params: Mapping[str, Any],
    context: Mapping[str, Any],
) -> Any:
    """Safely executes Python code and returns the value of 'result'."""

    # 1. Parse and Validate AST
    try:
        tree = ast.parse(logic_code, mode="exec")
    except SyntaxError as e:
        raise UnsafeLogicError(f"Syntax error in logic: {e}")

    _validate_ast(tree)

    # 2. Prepare Scope
    local_scope = {
        "input": input_value,
        "params": dict(params),
        "context": dict(context),
    }

    # Flatten dictionaries for direct access
    if isinstance(input_value, dict):
        for key, value in input_value.items():
            if _is_safe_variable_name(key):
                local_scope[key] = value

    for key, value in params.items():
        if _is_safe_variable_name(key):
            local_scope[key] = value

    # 3. Execute
    try:
        compiled = compile(tree, filename="<step.logic>", mode="exec")
        exec(compiled, _SAFE_GLOBALS, local_scope)
    except Exception as e:
        raise RuntimeError(f"Runtime error in logic execution: {e}")

    if "result" not in local_scope:
        raise UnsafeLogicError("Logic must assign a value to the 'result' variable.")

    return local_scope["result"]


def _validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeLogicError(f"Disallowed syntax: {type(node).__name__}")

        # Do not allow access to private attributes (._secret)
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise UnsafeLogicError("Access to private attributes is not allowed.")

        # Do not allow assignments to protected variables
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if node.id.startswith("_") or node.id in _SAFE_GLOBALS:
                raise UnsafeLogicError(
                    f"Cannot assign a value to protected variable: {node.id}"
                )
