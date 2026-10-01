import ast
import math
from typing import Any, Dict, Optional

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case

# --- THE AST WHITE-LIST YOU DEFINED ---
ALLOWED_NODE_TYPES = (
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.Load,
    ast.Store,
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
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.IfExp,
    ast.List,
    ast.Dict,
    ast.Tuple,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.Attribute,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.Call,
    ast.keyword,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    ast.GeneratorExp,
    ast.comprehension,
)

SAFE_GLOBALS = {
    "__builtins__": {},  # BLOCK EVERYTHING
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
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "reversed": reversed,
    "any": any,
    "all": all,
    "filter": filter,
    "map": map,
}

FORBIDDEN_ATTRS = frozenset(
    {
        "format",
        "format_map",
        "mro",
    }
)
FORBIDDEN_ATTR_PREFIXES = (
    "_",
    "gi_",
    "cr_",
    "ag_",
    "f_",
    "tb_",
)


def _is_forbidden_attr(attr: str) -> bool:
    return attr in FORBIDDEN_ATTRS or attr.startswith(FORBIDDEN_ATTR_PREFIXES)


class LogicProvider(ToolProvider):
    @tool(
        modifies_state=False,
        tests=[
            # arithmetic
            Case(
                {"expression": "1 + 2 * 3"}, {"result": 7, "success": True, "error": ""}
            ),
            Case(
                {"expression": "10 / 4"}, {"result": 2.5, "success": True, "error": ""}
            ),
            Case({"expression": "7 // 2"}, {"result": 3, "success": True, "error": ""}),
            Case({"expression": "7 % 3"}, {"result": 1, "success": True, "error": ""}),
            Case(
                {"expression": "2 ** 10"},
                {"result": 1024, "success": True, "error": ""},
            ),
            Case({"expression": "-5"}, {"result": -5, "success": True, "error": ""}),
            # comparisons and logic
            Case(
                {"expression": "1 < 2 < 3"},
                {"result": True, "success": True, "error": ""},
            ),
            Case(
                {"expression": "'a' in 'abc'"},
                {"result": True, "success": True, "error": ""},
            ),
            Case(
                {"expression": "1 if x else 2", "context": {"x": 0}},
                {"result": 2, "success": True, "error": ""},
            ),
            # context
            Case(
                {"expression": "x * 2", "context": {"x": 21}},
                {"result": 42, "success": True, "error": ""},
            ),
            Case(
                {
                    "expression": "sum([x for x in data if x > 10])",  # docstring example
                    "context": {"data": [1, 12, 5, 20]},
                },
                {"result": 32, "success": True, "error": ""},
            ),
            Case(
                {
                    "expression": "[x for x in range(5) if x > t]",  # context inside a comprehension
                    "context": {"t": 2},
                },
                {"result": [3, 4], "success": True, "error": ""},
            ),
            Case(
                {
                    "expression": "sum(x for x in range(5) if x > t)",  # context inside a generator
                    "context": {"t": 2},
                },
                {"result": 7, "success": True, "error": ""},
            ),
            # safe functions and constants
            Case(
                {"expression": "sqrt(16)"},
                {"result": 4.0, "success": True, "error": ""},
            ),
            Case(
                {"expression": "round(pi, 2)"},
                {"result": 3.14, "success": True, "error": ""},
            ),
            Case(
                {"expression": "round(3.14159, ndigits=2)"},
                {"result": 3.14, "success": True, "error": ""},
            ),
            Case(
                {"expression": "max(1, 5, 3)"},
                {"result": 5, "success": True, "error": ""},
            ),
            Case(
                {"expression": "sorted([3, 1, 2])"},
                {"result": [1, 2, 3], "success": True, "error": ""},
            ),
            Case(
                {"expression": "[i for i, v in enumerate(['a', 'b'])]"},
                {"result": [0, 1], "success": True, "error": ""},
            ),
            # data structures, strings, f-strings
            Case(
                {"expression": "{'a': 1}['a']"},
                {"result": 1, "success": True, "error": ""},
            ),
            Case(
                {"expression": "[1, 2, 3][1:]"},
                {"result": [2, 3], "success": True, "error": ""},
            ),
            Case(
                {"expression": "'abc'.upper()"},
                {"result": "ABC", "success": True, "error": ""},
            ),
            Case(
                {"expression": "f'{x}!'", "context": {"x": 5}},
                {"result": "5!", "success": True, "error": ""},
            ),
            # forbidden nodes
            Case(
                {"expression": "lambda: 1"},
                {
                    "result": None,
                    "success": False,
                    "error": "Security Breach: Forbidden operation detected: Lambda",
                },
            ),
            Case(
                {"expression": "(y := 1)"},
                {
                    "result": None,
                    "success": False,
                    "error": "Security Breach: Forbidden operation detected: NamedExpr",
                },
            ),
            # forbidden attributes
            Case(
                {"expression": "().__class__"},
                {
                    "result": None,
                    "success": False,
                    "error": "Security Breach: Access to attribute __class__ is forbidden.",
                },
            ),
            Case(
                {"expression": "(i for i in [1]).gi_frame"},
                {
                    "result": None,
                    "success": False,
                    "error": "Security Breach: Access to attribute gi_frame is forbidden.",
                },
            ),
            Case(
                {"expression": "'{0.__class__}'.format(1)"},
                {
                    "result": None,
                    "success": False,
                    "error": "Security Breach: Access to attribute format is forbidden.",
                },
            ),
            # builtins are blocked
            Case(
                {"expression": "__import__('os')"},
                {"result": None, "success": False, "error": str},
            ),
            Case(
                {"expression": "open('a.txt')"},
                {"result": None, "success": False, "error": str},
            ),
            # ordinary errors
            Case(
                {"expression": "1 / 0"},
                {"result": None, "success": False, "error": "division by zero"},
            ),
            Case(
                {"expression": "y + 1"},  # missing variable
                {"result": None, "success": False, "error": str},
            ),
            Case(
                {"expression": "1 +"},  # syntax error
                {"result": None, "success": False, "error": str},
            ),
            Case(
                {"expression": ""},  # empty expression
                {"result": None, "success": False, "error": str},
            ),
            Case(
                {"expression": "import os"},  # statements are not expressions
                {"result": None, "success": False, "error": str},
            ),
        ],
    )
    def evaluate(
        self, expression: str, context: Optional[Dict[str, Any]] = None
    ) -> Return(result=Any, success=bool, error=str):
        """
        Evaluates a mathematical or logical Python expression safely. Allows basic arithmetic, comparisons, list/dict comprehensions, and a set of safe math functions. Example: expression="sum([x for x in data if x > 10])", context={"data": [1, 12, 5, 20]}
        """
        try:
            tree = ast.parse(expression, mode="eval")

            for node in ast.walk(tree):
                if type(node) not in ALLOWED_NODE_TYPES and not isinstance(
                    node, ast.Expression
                ):
                    return {
                        "result": None,
                        "success": False,
                        "error": f"Security Breach: Forbidden operation detected: {type(node).__name__}",
                    }

                if isinstance(node, ast.Attribute) and _is_forbidden_attr(node.attr):
                    return {
                        "result": None,
                        "success": False,
                        "error": f"Security Breach: Access to attribute {node.attr} is forbidden.",
                    }

            # A single dict as globals so comprehensions and generators can see the context.
            # "__builtins__" goes last so the context cannot restore it.
            namespace = {**SAFE_GLOBALS, **(context or {}), "__builtins__": {}}

            # pylint: disable=eval-used
            result = eval(compile(tree, "<dynamic_logic>", "eval"), namespace)
            # pylint: enable=eval-used

            return {"result": result, "success": True, "error": ""}

        except Exception as e:
            return {"result": None, "success": False, "error": str(e)}
