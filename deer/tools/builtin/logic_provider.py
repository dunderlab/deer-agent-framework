import ast
import math
import logging
from typing import Any, Dict

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return

logger = logging.getLogger("DEER-LLM")

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


class LogicProvider(ToolProvider):
    @tool(modifies_state=False)
    def evaluate(self, expression: str, context: Dict[str, Any]) -> Return(result=Any):
        """
        Evaluates a mathematical or logical Python expression safely.
        Allows basic arithmetic, comparisons, list/dict comprehensions,
        and a set of safe math functions.

        Example: expression="sum([x for x in data if x > 10])", context={"data": [1, 12, 5, 20]}
        """
        try:
            # 1. Parse the expression into an AST
            tree = ast.parse(expression, mode="eval")

            # 2. SECURITY CHECK: Verify all nodes are in the whitelist
            for node in ast.walk(tree):
                if type(node) not in ALLOWED_NODE_TYPES:
                    raise RuntimeError(
                        f"Security Breach: Forbidden operation detected: {type(node).__name__}"
                    )

            # 3. EXECUTION: Evaluate the AST using the safe globals and the provided context
            # We use the 'context' as the locals dictionary for the eval
            result = eval(
                compile(tree, filename="<dynamic_logic>", mode="eval"),
                SAFE_GLOBALS,
                context,
            )

            return {"result": result}

        except Exception as e:
            logger.error(f"Logic Evaluation Error: {e}")
            return {"result": None, "error": str(e)}
