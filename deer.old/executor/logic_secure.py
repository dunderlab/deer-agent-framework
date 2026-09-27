import ast
import math

# Allowed nodes to support mathematical logic, strings, and basic assignments
ALLOWED_NODE_TYPES = (
    # --- Basic Structure ---
    ast.Module,  # Root container
    ast.Expr,  # Standalone expressions
    ast.Assign,  # Variable assignment (e.g., x = 10)
    ast.Load,  # Load variable value
    ast.Store,  # Store variable value
    ast.Name,  # Variable names
    ast.Constant,  # Literal values (numbers, strings, None, True, False)
    # --- Mathematical Operations ---
    ast.BinOp,  # Binary operations (+, -, *, /)
    ast.UnaryOp,  # Unary operations (not, -x)
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    # --- Logic and Comparison ---
    ast.Compare,  # Comparisons (==, !=, <, etc.)
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.BoolOp,  # Logical operators (and, or)
    ast.And,
    ast.Or,
    ast.IfExp,  # Ternary expressions (x if condition else y)
    # --- Data Structures and Access ---
    ast.List,  # [1, 2, 3]
    ast.Dict,  # {'a': 1}
    ast.Tuple,  # (1, 2)
    ast.Set,  # {1, 2}
    ast.Subscript,  # Indexed/key access: list[0] or dict['k']
    ast.Slice,  # Slicing: list[1:5]
    ast.Attribute,  # Attribute access: object.property (required for Pydantic)
    # --- Strings and Formatting ---
    ast.JoinedStr,  # f-strings
    ast.FormattedValue,  # Values inside f-strings
    # --- Calls and Functions ---
    ast.Call,  # Allow calling functions from _SAFE_GLOBALS
    ast.keyword,  # Keyword arguments: func(x=1)
    # --- Advanced Safe Flexibility ---
    ast.ListComp,  # [x for x in items] (useful for data transformation)
    ast.DictComp,  # {k: v for k, v in items}
    ast.comprehension,  # Internal comprehension logic
)

SAFE_GLOBALS = {
    # --- Sandbox Privacy ---
    "__builtins__": {},  # Blocks access to dangerous functions like eval, exec, open
    # --- Mathematical Constants ---
    "pi": math.pi,
    "e": math.e,
    # --- Arithmetic and Numbers ---
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
    # --- Type Conversion (Casting) ---
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    # --- Collection Processing ---
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,  # Allows safe list sorting
    "reversed": reversed,
    # --- Advanced Logic ---
    "any": any,  # Is any value True?
    "all": all,  # Are all values True?
    "filter": filter,
    "map": map,
}
