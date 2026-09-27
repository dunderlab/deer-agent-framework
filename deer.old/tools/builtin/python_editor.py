from dataclasses import dataclass
from deer.tools import ToolProvider, tool
from deer.schema import Return
import libcst as cst
from typing import Optional


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

        # Search for the method in the class body
        for i, stmt in enumerate(new_body):
            if (
                isinstance(stmt, cst.FunctionDef)
                and stmt.name.value == self.method_name
            ):
                new_body[i] = self.new_method_node
                self.method_found = True
                break

        if not self.method_found:
            # Append method with proper spacing if class isn't empty
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
                is_import = any(
                    isinstance(b, (cst.Import, cst.ImportFrom)) for b in stmt.body
                )
                if is_import:
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
            new_body = []
            for stmt in updated_node.body.body:
                if (
                    isinstance(stmt, cst.FunctionDef)
                    and stmt.name.value == self.target_name
                ):
                    self.found = True
                    continue
                new_body.append(stmt)
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
class PythonEditor(ToolProvider):

    @tool(modifies_state=True)
    def add_function(
        self, path: str, function: str
    ) -> Return(success=bool, message=str):
        """Upserts a top-level function in a Python file using AST-based editing to maintain formatting and integrity."""
        safe_path = self.jailed_path(path)

        # Parse the new function
        try:
            new_fn_module = cst.parse_module(function.strip())
            new_fn_node = None
            for stmt in new_fn_module.body:
                if isinstance(stmt, cst.FunctionDef):
                    new_fn_node = stmt
                    break

            if not new_fn_node:
                return {
                    "success": False,
                    "message": "Error: No function definition found in the provided string.",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error parsing new function: {str(e)}",
            }

        # Read and parse the target file
        try:
            if safe_path.exists():
                with open(safe_path, "r", encoding="utf-8") as f:
                    content = f.read()
                module_cst = cst.parse_module(content)
            else:
                # If file doesn't exist, create an empty module
                module_cst = cst.Module(body=[])
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading or parsing target file: {str(e)}",
            }

        # Transform the CST
        transformer = FunctionTransformer(new_fn_node)
        modified_cst = module_cst.visit(transformer)

        if not transformer.found:
            # If not found, append to the end
            new_body = list(modified_cst.body)
            # Add two empty lines before the new function if the file wasn't empty
            if new_body:
                new_fn_node = new_fn_node.with_changes(
                    leading_lines=(cst.EmptyLine(), cst.EmptyLine())
                )
            new_body.append(new_fn_node)
            modified_cst = modified_cst.with_changes(body=new_body)

        # Write back to file
        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(modified_cst.code)
        except Exception as e:
            return {
                "success": False,
                "message": f"Error writing to file: {str(e)}",
            }

        return {
            "success": True,
            "message": f"Function '{new_fn_node.name.value}' {'updated' if transformer.found else 'added'} successfully in {path}.",
        }

    @tool(modifies_state=True)
    def add_method(
        self, path: str, class_name: str, function: str
    ) -> Return(success=bool, message=str):
        """Upserts a method inside a target class using AST transformation, replacing existing or appending at the end."""
        safe_path = self.jailed_path(path)

        # Parse the new method
        try:
            new_fn_module = cst.parse_module(function.strip())
            new_method_node = None
            for stmt in new_fn_module.body:
                if isinstance(stmt, cst.FunctionDef):
                    new_method_node = stmt
                    break

            if not new_method_node:
                return {
                    "success": False,
                    "message": "Error: No function/method definition found in the provided string.",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error parsing new method: {str(e)}",
            }

        # Read and parse the target file
        try:
            if not safe_path.exists():
                return {
                    "success": False,
                    "message": f"Error: Target file {path} does not exist.",
                }
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            module_cst = cst.parse_module(content)
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading or parsing target file: {str(e)}",
            }

        # Transform the CST
        transformer = MethodTransformer(class_name, new_method_node)
        modified_cst = module_cst.visit(transformer)

        if not transformer.class_found:
            return {
                "success": False,
                "message": f"Error: Class '{class_name}' not found in {path}.",
            }

        # Write back to file
        try:
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(modified_cst.code)
        except Exception as e:
            return {
                "success": False,
                "message": f"Error writing to file: {str(e)}",
            }

        status = "updated" if transformer.method_found else "added"
        return {
            "success": True,
            "message": f"Method '{new_method_node.name.value}' {status} successfully in class '{class_name}' within {path}.",
        }

    @tool(modifies_state=True)
    def add_class(
        self, path: str, class_code: str
    ) -> Return(success=bool, message=str):
        """Upserts a class definition in a Python file, replacing an existing class by name or appending it at EOF."""

        safe_path = self.jailed_path(path)

        # Parse the new class
        try:
            new_class_module = cst.parse_module(class_code.strip())
            new_class_node = None
            for stmt in new_class_module.body:
                if isinstance(stmt, cst.ClassDef):
                    new_class_node = stmt
                    break

            if not new_class_node:
                return {
                    "success": False,
                    "message": "Error: No class definition found in the provided string.",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error parsing new class: {str(e)}",
            }

        # Read and parse the target file
        try:
            if safe_path.exists():
                with open(safe_path, "r", encoding="utf-8") as f:
                    content = f.read()
                module_cst = cst.parse_module(content)
            else:
                # If file doesn't exist, create an empty module
                module_cst = cst.Module(body=[])
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading or parsing target file: {str(e)}",
            }

        # Transform the CST
        transformer = ClassTransformer(new_class_node)
        modified_cst = module_cst.visit(transformer)

        if not transformer.found:
            # If not found, append to the end
            new_body = list(modified_cst.body)
            # Add two empty lines before the new class if the file wasn't empty
            if new_body:
                new_class_node = new_class_node.with_changes(
                    leading_lines=(cst.EmptyLine(), cst.EmptyLine())
                )
            new_body.append(new_class_node)
            modified_cst = modified_cst.with_changes(body=new_body)

        # Write back to file
        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(modified_cst.code)
        except Exception as e:
            return {
                "success": False,
                "message": f"Error writing to file: {str(e)}",
            }

        status = "updated" if transformer.found else "added"
        return {
            "success": True,
            "message": f"Class '{new_class_node.name.value}' {status} successfully in {path}.",
        }

    @tool(modifies_state=True)
    def add_import(
        self, path: str, import_code: str
    ) -> Return(success=bool, message=str):
        """Inserts a unique import statement at the top of a file, avoiding duplicates and respecting PEP 8 order."""
        safe_path = self.jailed_path(path)
        try:
            new_import_module = cst.parse_module(import_code.strip())
            if not new_import_module.body:
                return {"success": False, "message": "Error: Invalid import code."}
            new_import_node = new_import_module.body[0]
        except Exception as e:
            return {"success": False, "message": f"Error parsing import: {str(e)}"}

        try:
            if safe_path.exists():
                with open(safe_path, "r", encoding="utf-8") as f:
                    content = f.read()
                module_cst = cst.parse_module(content)
            else:
                module_cst = cst.Module(body=[])

            transformer = ImportTransformer(new_import_node)
            modified_cst = module_cst.visit(transformer)

            if transformer.already_exists:
                return {
                    "success": True,
                    "message": f"Import already exists in {path}.",
                }

            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(modified_cst.code)
            return {"success": True, "message": f"Import added successfully to {path}."}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def remove_function(
        self, path: str, function_name: str
    ) -> Return(success=bool, message=str):
        """Deletes a top-level function definition and its associated whitespace from the target Python file."""
        return self._remove_element(path, function_name, cst.FunctionDef)

    @tool(modifies_state=True)
    def remove_class(
        self, path: str, class_name: str
    ) -> Return(success=bool, message=str):
        """Deletes a top-level class definition and all its members from the target Python file surgically."""
        return self._remove_element(path, class_name, cst.ClassDef)

    @tool(modifies_state=True)
    def remove_method(
        self, path: str, class_name: str, method_name: str
    ) -> Return(success=bool, message=str):
        """Deletes a specific method from a target class while preserving the rest of the class structure."""
        return self._remove_element(
            path, method_name, cst.FunctionDef, class_name=class_name
        )

    def _remove_element(self, path, name, type_, class_name=None):
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            module_cst = cst.parse_module(content)

            transformer = RemovalTransformer(name, type_, class_name=class_name)
            modified_cst = module_cst.visit(transformer)

            if not transformer.found:
                msg = f"{type_.__name__} '{name}' not found"
                if class_name:
                    msg += f" in class '{class_name}'"
                return {"success": False, "message": msg}

            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(modified_cst.code)
            return {
                "success": True,
                "message": f"Element removed successfully from {path}.",
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool()
    def list_elements(self, path: str) -> Return(elements=list):
        """Analyzes the file's structure and returns a map of all top-level functions, classes, and their methods."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"elements": [], "message": f"File {path} not found."}
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            module_cst = cst.parse_module(content)
            visitor = ListElementsVisitor()
            module_cst.visit(visitor)
            return {"elements": visitor.elements}
        except Exception as e:
            return {"elements": [], "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def rename_element(
        self, path: str, old_name: str, new_name: str
    ) -> Return(success=bool, message=str):
        """Updates the identifier of a top-level function or class definition across its declaration in the file."""
        safe_path = self.jailed_path(path)
        try:
            if not safe_path.exists():
                return {"success": False, "message": f"File {path} not found."}
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            module_cst = cst.parse_module(content)
            transformer = RenameTransformer(old_name, new_name)
            modified_cst = module_cst.visit(transformer)

            if not transformer.found:
                return {
                    "success": False,
                    "message": f"Element '{old_name}' not found in {path}.",
                }

            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(modified_cst.code)
            return {
                "success": True,
                "message": f"Element renamed from '{old_name}' to '{new_name}' in {path}.",
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
