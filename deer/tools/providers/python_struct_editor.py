import libcst as cst
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case

# Common files for all tests
_TEST_FILES = {
    "module.py": "import os\n\ndef old_func():\n    pass\n\nclass MyClass:\n    def old_method(self):\n        pass",
}

# Reusing the success pattern from previous tools
EXPECTED_SUCCESS = {"success": True, "message": str}

# --- CST Transformers ---
# Kept as internal helpers to maintain clean tool interface


class FunctionTransformer(cst.CSTTransformer):
    def __init__(self, new_func_node: cst.FunctionDef):
        self.new_func_node = new_func_node
        self.func_name = new_func_node.name.value
        self.found = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if original_node.name.value == self.func_name:
            self.found = True
            return self.new_func_node
        return updated_node


class MethodTransformer(cst.CSTTransformer):
    def __init__(self, class_name: str, new_method_node: cst.FunctionDef):
        self.class_name = class_name
        self.new_method_node = new_method_node
        self.method_name = new_method_node.name.value
        self.class_found = False
        self.method_found = False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.class_name:
            return updated_node
        self.class_found = True
        new_body = list(updated_node.body.body)
        for i, stmt in enumerate(new_body):
            if (
                isinstance(stmt, cst.FunctionDef)
                and stmt.name.value == self.method_name
            ):
                new_body[i] = self.new_method_node
                self.method_found = True
                break
        if not self.method_found:
            if new_body:
                self.new_method_node = self.new_method_node.with_changes(
                    leading_lines=(cst.EmptyLine(),)
                )
            new_body.append(self.new_method_node)
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )


class ClassTransformer(cst.CSTTransformer):
    def __init__(self, new_class_node: cst.ClassDef):
        self.new_class_node = new_class_node
        self.class_name = new_class_node.name.value
        self.found = False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value == self.class_name:
            self.found = True
            return self.new_class_node
        return updated_node


class ImportTransformer(cst.CSTTransformer):
    def __init__(self, new_import_node: cst.CSTNode):
        self.new_import_node = new_import_node
        self.already_exists = False

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        new_code = cst.Module([]).code_for_node(self.new_import_node).strip()
        for stmt in original_node.body:
            if cst.Module([]).code_for_node(stmt).strip() == new_code:
                self.already_exists = True
                return updated_node
        insert_idx = 0
        for i, stmt in enumerate(updated_node.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                if any(isinstance(b, (cst.Import, cst.ImportFrom)) for b in stmt.body):
                    insert_idx = i + 1
                else:
                    break
            elif isinstance(stmt, (cst.Comment, cst.EmptyLine)):
                continue
            else:
                break
        new_body = list(updated_node.body)
        new_body.insert(insert_idx, self.new_import_node)
        return updated_node.with_changes(body=new_body)


class RemovalTransformer(cst.CSTTransformer):
    def __init__(
        self, target_name: str, target_type: type, class_name: Optional[str] = None
    ):
        self.target_name = target_name
        self.target_type = target_type
        self.class_name = class_name
        self.found = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> Optional[cst.FunctionDef]:
        if (
            not self.class_name
            and isinstance(original_node, self.target_type)
            and original_node.name.value == self.target_name
        ):
            self.found = True
            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> Optional[cst.ClassDef]:
        if self.class_name and original_node.name.value == self.class_name:
            new_body = [
                s
                for s in updated_node.body.body
                if not (
                    isinstance(s, cst.FunctionDef) and s.name.value == self.target_name
                )
            ]
            if len(new_body) < len(updated_node.body.body):
                self.found = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )
        if (
            not self.class_name
            and isinstance(original_node, self.target_type)
            and original_node.name.value == self.target_name
        ):
            self.found = True
            return cst.RemovalSentinel.REMOVE
        return updated_node


class RenameTransformer(cst.CSTTransformer):
    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name
        self.found = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if original_node.name.value == self.old_name:
            self.found = True
            return updated_node.with_changes(name=cst.Name(self.new_name))
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value == self.old_name:
            self.found = True
            return updated_node.with_changes(name=cst.Name(self.new_name))
        return updated_node


class ListElementsVisitor(cst.CSTVisitor):
    def __init__(self):
        self.elements = []

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        methods = [
            m.name.value for m in node.body.body if isinstance(m, cst.FunctionDef)
        ]
        self.elements.append(
            {"type": "class", "name": node.name.value, "methods": methods}
        )
        return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self.elements.append({"type": "function", "name": node.name.value})
        return False


@dataclass
class PythonStructEditor(ToolProvider):
    """
    Advanced structural editor for Python code using Concrete Syntax Trees (CST).
    Allows surgically adding, updating, removing, and renaming functions, classes, and imports
    without destroying the original code's formatting.
    """

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "module.py", "function_code": "def new_func():\n    pass"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            Case(
                {
                    "path": "module.py",
                    "function_code": "def old_func():\n    print('updated')",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ],
    )
    def upsert_function(
        self, path: str, function_code: str
    ) -> Return(success=bool, message=str):
        """Adds a top-level function or updates an existing one if the name matches. 'function_code' must be a valid Python function definition."""
        safe_path = self.jailed_path(path)
        try:
            new_fn_module = cst.parse_module(function_code.strip())
            new_fn_node = next(
                (s for s in new_fn_module.body if isinstance(s, cst.FunctionDef)), None
            )
            if not new_fn_node:
                return {
                    "success": False,
                    "message": "No valid function definition found in provided code.",
                }

            content = (
                safe_path.read_text(encoding="utf-8") if safe_path.exists() else ""
            )
            module_cst = cst.parse_module(content)

            transformer = FunctionTransformer(new_fn_node)
            modified_cst = module_cst.visit(transformer)
            if not transformer.found:
                new_body = list(modified_cst.body)
                if new_body:
                    new_fn_node = new_fn_node.with_changes(
                        leading_lines=(cst.EmptyLine(), cst.EmptyLine())
                    )
                new_body.append(new_fn_node)
                modified_cst = modified_cst.with_changes(body=new_body)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(modified_cst.code, encoding="utf-8")
            return {
                "success": True,
                "message": f"Function '{new_fn_node.name.value}' upserted successfully.",
            }
        except Exception as e:
            return {"success": False, "message": f"Structural edit error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {
                    "path": "module.py",
                    "class_name": "MyClass",
                    "method_code": "def new_method(self):\n    pass",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            Case(
                {
                    "path": "module.py",
                    "class_name": "MyClass",
                    "method_code": "def old_method(self):\n    print('updated')",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ],
    )
    def upsert_method(
        self, path: str, class_name: str, method_code: str
    ) -> Return(success=bool, message=str):
        """Adds a method to a specific class or updates it if the name matches. 'method_code' must be a valid Python function definition."""
        safe_path = self.jailed_path(path)
        try:
            new_fn_module = cst.parse_module(method_code.strip())
            new_method_node = next(
                (s for s in new_fn_module.body if isinstance(s, cst.FunctionDef)), None
            )
            if not new_method_node:
                return {
                    "success": False,
                    "message": "No valid method definition found in provided code.",
                }

            content = safe_path.read_text(encoding="utf-8")
            module_cst = cst.parse_module(content)

            transformer = MethodTransformer(class_name, new_method_node)
            modified_cst = module_cst.visit(transformer)
            if not transformer.class_found:
                return {"success": False, "message": f"Class '{class_name}' not found."}

            safe_path.write_text(modified_cst.code, encoding="utf-8")
            return {
                "success": True,
                "message": f"Method '{new_method_node.name.value}' upserted in '{class_name}'.",
            }
        except Exception as e:
            return {"success": False, "message": f"Structural edit error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "module.py", "class_code": "class NewClass:\n    pass"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            Case(
                {
                    "path": "module.py",
                    "class_code": "class MyClass:\n    pass\n    def updated(self): pass",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ],
    )
    def upsert_class(
        self, path: str, class_code: str
    ) -> Return(success=bool, message=str):
        """Adds a top-level class or updates an existing one. 'class_code' must be a valid Python class definition."""
        safe_path = self.jailed_path(path)
        try:
            new_cl_module = cst.parse_module(class_code.strip())
            new_class_node = next(
                (s for s in new_cl_module.body if isinstance(s, cst.ClassDef)), None
            )
            if not new_class_node:
                return {"success": False, "message": "No valid class definition found."}

            content = (
                safe_path.read_text(encoding="utf-8") if safe_path.exists() else ""
            )
            module_cst = cst.parse_module(content)

            transformer = ClassTransformer(new_class_node)
            modified_cst = module_cst.visit(transformer)
            if not transformer.found:
                new_body = list(modified_cst.body)
                if new_body:
                    new_class_node = new_class_node.with_changes(
                        leading_lines=(cst.EmptyLine(), cst.EmptyLine())
                    )
                new_body.append(new_class_node)
                modified_cst = modified_cst.with_changes(body=new_body)

            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(modified_cst.code, encoding="utf-8")
            return {
                "success": True,
                "message": f"Class '{new_class_node.name.value}' upserted successfully.",
            }
        except Exception as e:
            return {"success": False, "message": f"Structural edit error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "module.py", "import_code": "import sys"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            Case(
                {"path": "module.py", "import_code": "import os"},  # Duplicate
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ],
    )
    def upsert_import(
        self, path: str, import_code: str
    ) -> Return(success=bool, message=str):
        """Inserts a unique import statement at the top of the file. Avoids duplicates and preserves order."""
        safe_path = self.jailed_path(path)
        try:
            new_import_module = cst.parse_module(import_code.strip())
            if not new_import_module.body:
                return {"success": False, "message": "Invalid import code."}
            new_import_node = new_import_module.body[0]

            content = (
                safe_path.read_text(encoding="utf-8") if safe_path.exists() else ""
            )
            module_cst = cst.parse_module(content)

            transformer = ImportTransformer(new_import_node)
            modified_cst = module_cst.visit(transformer)
            if transformer.already_exists:
                return {"success": True, "message": "Import already exists."}

            safe_path.write_text(modified_cst.code, encoding="utf-8")
            return {"success": True, "message": "Import added successfully."}
        except Exception as e:
            return {"success": False, "message": f"Structural edit error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            # Remove function
            Case(
                {"path": "module.py", "name": "old_func", "element_type": "function"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            # Remove class
            Case(
                {"path": "module.py", "name": "MyClass", "element_type": "class"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            # Remove method
            Case(
                {
                    "path": "module.py",
                    "name": "old_method",
                    "element_type": "method",
                    "class_name": "MyClass",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            # Fail: element not found
            Case(
                {"path": "module.py", "name": "ghost", "element_type": "function"},
                {"success": False, "message": str},
                files=_TEST_FILES,
            ),
        ],
    )
    def delete_element(
        self,
        path: str,
        name: str,
        element_type: Literal["function", "class", "method"],
        class_name: Optional[str] = None,
    ) -> Return(success=bool, message=str):
        """Surgically removes a function, class, or method from a file. For methods, 'class_name' is required."""
        safe_path = self.jailed_path(path)
        type_map = {
            "function": cst.FunctionDef,
            "class": cst.ClassDef,
            "method": cst.FunctionDef,
        }

        try:
            if not safe_path.exists():
                return {"success": False, "message": "File not found."}
            content = safe_path.read_text(encoding="utf-8")
            module_cst = cst.parse_module(content)

            transformer = RemovalTransformer(
                name, type_map[element_type], class_name=class_name
            )
            modified_cst = module_cst.visit(transformer)
            if not transformer.found:
                return {"success": False, "message": f"Element '{name}' not found."}

            safe_path.write_text(modified_cst.code, encoding="utf-8")
            return {
                "success": True,
                "message": f"{element_type} '{name}' removed successfully.",
            }
        except Exception as e:
            return {"success": False, "message": f"Structural edit error: {str(e)}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {
                    "path": "module.py",
                    "old_name": "old_func",
                    "new_name": "renamed_func",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            Case(
                {
                    "path": "module.py",
                    "old_name": "MyClass",
                    "new_name": "RenamedClass",
                },
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ],
    )
    def rename_identifier(
        self, path: str, old_name: str, new_name: str
    ) -> Return(success=bool, message=str):
        """Renames a top-level function or class declaration. Does not update calls to this element."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": "File not found."}
            content = safe_path.read_text(encoding="utf-8")
            module_cst = cst.parse_module(content)

            transformer = RenameTransformer(old_name, new_name)
            modified_cst = module_cst.visit(transformer)
            if not transformer.found:
                return {
                    "success": False,
                    "message": f"Identifier '{old_name}' not found.",
                }

            safe_path.write_text(modified_cst.code, encoding="utf-8")
            return {
                "success": True,
                "message": f"Renamed '{old_name}' to '{new_name}'.",
            }
        except Exception as e:
            return {"success": False, "message": f"Structural edit error: {str(e)}"}

    @tool(
        tests=[
            Case({"path": "module.py"}, {"elements": list}, files=_TEST_FILES),
        ]
    )
    def analyze_structure(self, path: str) -> Return(elements=List[Dict[str, Any]]):
        """Returns a map of all top-level functions, classes, and their internal methods. Use this to understand a file's API before editing."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"elements": []}
            content = safe_path.read_text(encoding="utf-8")
            module_cst = cst.parse_module(content)
            visitor = ListElementsVisitor()
            module_cst.visit(visitor)
            return {"elements": visitor.elements}
        except Exception as e:
            return {"elements": [], "message": f"Analysis error: {str(e)}"}
