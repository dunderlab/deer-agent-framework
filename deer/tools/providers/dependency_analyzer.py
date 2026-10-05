import libcst as cst
from dataclasses import dataclass
from typing import List, Dict, Any

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Return, Case

# --- CST Visitors for Analysis ---


class ReferenceVisitor(cst.CSTVisitor):
    """Visitor that finds all occurrences of a specific identifier name."""

    def __init__(self, target_name: str):
        self.target_name = target_name
        self.occurrences = []

    def visit_Name(self, node: cst.Name) -> None:
        if node.value == self.target_name:
            # We capture the node to get position info later if needed
            self.occurrences.append(node)


class ImportVisitor(cst.CSTVisitor):
    """Visitor that extracts all imports from a module."""

    def __init__(self):
        self.imports = []

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            self.imports.append({"type": "module", "name": alias.name.value})

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = node.module.value if node.module else "unknown"
        for alias in node.names:
            self.imports.append(
                {"type": "object", "module": module, "name": alias.name.value}
            )


class DefinitionVisitor(cst.CSTVisitor):
    """Visitor that finds all top-level definitions (functions and classes)."""

    def __init__(self):
        self.definitions = set()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.definitions.add(node.name.value)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.definitions.add(node.name.value)


@dataclass
class DependencyAnalyzer(ToolProvider):
    """
    Analyzes Python code to map relationships between identifiers,
    imports, and definitions. Used for impact analysis before refactoring.
    """

    # Setup for TDD
    _TEST_FILES = {
        "main.py": "from utils import helper\n\ndef start():\n    helper()\n    do_work()",
        "utils.py": "def helper():\n    print('helping')\n\ndef unused_func():\n    pass",
    }

    @tool(
        tests=[
            Case(
                {"path": ".", "identifier": "helper"},
                {
                    "references": list,
                    "count": 3,
                },  # 1 def in utils.py, 1 import in main.py, 1 call in main.py
                files=_TEST_FILES,
            ),
            Case(
                {"path": ".", "identifier": "non_existent"},
                {"references": [], "count": 0},
                files=_TEST_FILES,
            ),
        ]
    )
    def find_references(
        self, path: str, identifier: str
    ) -> Return(references=List[Dict[str, Any]], count=int):
        """Searches the entire project for all usages of a specific identifier (function or class name).
        Essential for understanding the impact of changing a definition."""
        root_path = self.jailed_path(path)
        all_refs = []

        # Walk through all python files
        for py_file in root_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                module = cst.parse_module(content)
                visitor = ReferenceVisitor(identifier)
                module.visit(visitor)

                for _ in visitor.occurrences:
                    # We add the file and a placeholder for position (CST positions can be complex)
                    all_refs.append(
                        {
                            "file": str(py_file.relative_to(root_path)),
                            "identifier": identifier,
                        }
                    )
            except Exception:
                continue

        return {"references": all_refs, "count": len(all_refs)}

    @tool(
        tests=[
            Case({"path": "main.py"}, {"imports": list}, files=_TEST_FILES),
        ]
    )
    def analyze_imports(self, path: str) -> Return(imports=List[Dict[str, Any]]):
        """Maps all import statements in a file. Use this to understand external dependencies and module hierarchy."""
        safe_path = self.jailed_path(path)
        try:
            content = safe_path.read_text(encoding="utf-8")
            module = cst.parse_module(content)
            visitor = ImportVisitor()
            module.visit(visitor)
            return {"imports": visitor.imports}
        except Exception as e:
            return {"imports": [], "error": str(e)}

    @tool(
        tests=[
            Case(
                {"path": "utils.py"},
                {"unused": ["helper", "unused_func"]},
                files=_TEST_FILES,
            ),
        ]
    )
    def find_unused_definitions(self, path: str) -> Return(unused=List[str]):
        """Identifies top-level functions and classes that are defined but never referenced within the same file."""
        safe_path = self.jailed_path(path)
        try:
            content = safe_path.read_text(encoding="utf-8")
            module = cst.parse_module(content)

            # 1. Find all definitions
            def_visitor = DefinitionVisitor()
            module.visit(def_visitor)
            defs = def_visitor.definitions

            # 2. Find all name usages
            # ref_visitor = ReferenceVisitor("")  # dummy name

            # Custom override to collect ALL names
            class AllNameVisitor(cst.CSTVisitor):
                def __init__(self):
                    self.names = set()

                def visit_Name(self, node):
                    self.names.add(node.value)

            all_names_visitor = AllNameVisitor()
            module.visit(all_names_visitor)

            # A definition is unused if it's only mentioned once (its own definition)
            # This is a simplified heuristic for a single-file analysis
            unused = []
            # Note: This is a naive check; true unused detection requires global analysis
            # but it's highly useful for cleaning up local files.
            for d in defs:
                # Count occurrences of the name in the whole file
                # If it only appears in its own definition, it's potentially unused
                # count = 0
                # Re-scan the module for this specific name
                v = ReferenceVisitor(d)
                module.visit(v)
                if len(v.occurrences) <= 1:
                    unused.append(d)

            return {"unused": sorted(unused)}
        except Exception as e:
            return {"unused": [], "error": str(e)}
