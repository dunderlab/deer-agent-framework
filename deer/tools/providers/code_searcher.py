import os
from dataclasses import dataclass
from typing import List

from deer.tools import tool
from deer.tools.schemas import CommandOut, Case
from .base.base_command_runner import BaseCommandRunner

# Constants moved outside to prevent NameError
EXPECTED_SUCCESS = {
    "stdout": str,
    "stderr": str,
    "returncode": 0,
    "message": str,
}


@dataclass
class CodeSearcher(BaseCommandRunner):
    """
    Advanced codebase search tool based on ripgrep (rg).
    Used for finding text patterns, locating files, and analyzing project structure.
    """

    _TEST_FILES = {
        "app.py": "def hello():\n    print('hello world')",
        "utils.py": "def goodbye():\n    print('hello world')",
        "README.md": "# Project Title\nThis is a sample project.",
        "config.json": '{"version": "1.0", "env": "dev"}',
    }

    @property
    def allowed_commands(self):
        return ["rg"]

    def _execute_command(
        self, binary: str, args: List[str], path: str, timeout_seconds: int = 60
    ) -> CommandOut:
        path = self.jailed_path(path)
        result = super()._execute_command(binary, args, path, timeout_seconds)

        raw_output = result.get("stdout")
        if not raw_output:
            return result

        absolute_lines = []
        for line in raw_output.splitlines():
            if ":" in line:
                # 1. Separamos la ruta relativa que dio rg del resto de la línea
                relative_to_cwd, separator, rest = line.partition(":")

                # 2. Construimos la ruta absoluta REAL en el sistema de archivos del host
                # path = directorio donde se ejecutó el comando
                # relative_to_cwd = ruta que devolvió rg
                full_system_path = os.path.join(path, relative_to_cwd)

                # 3. AQUÍ ESTÁ LA MAGIA: Convertimos la ruta absoluta del host
                # en una ruta relativa a self.jail.
                # Esto elimina la parte de '/Users/yeison/...' y deja solo 'astropy/modeling/...'
                jail_relative_path = os.path.relpath(full_system_path, self.jail)

                # 4. Reconstruimos la línea para el agente
                absolute_lines.append(f"{jail_relative_path}{separator}{rest}")
            else:
                absolute_lines.append(line)

        result["stdout"] = "\n".join(absolute_lines)
        return result

    @tool(
        tests=[
            Case(
                {"path": ".", "query": "hello world"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def search_text_literal(self, path: str, query: str) -> CommandOut:
        """Finds literal fixed-string matches in all files under 'path'. Returns file paths, line numbers, and content."""
        return self._execute_command(
            "rg",
            [
                "--fixed-strings",
                "--line-number",
                "--column",
                "--no-heading",
                query,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "pattern": r"def\s+\w+\(\)"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def search_text_regex(self, path: str, pattern: str) -> CommandOut:
        """Finds text using PCRE2 regex patterns in all files under 'path'. Returns file paths, line numbers, and content."""
        return self._execute_command(
            "rg",
            [
                "--line-number",
                "--column",
                "--no-heading",
                pattern,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "query": "PROJECT"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def search_text_insensitive(self, path: str, query: str) -> CommandOut:
        """Finds literal text matches ignoring case in all files under 'path'. Returns file paths, line numbers, and content."""
        return self._execute_command(
            "rg",
            [
                "--fixed-strings",
                "--ignore-case",
                "--line-number",
                "--column",
                "--no-heading",
                query,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "pattern": r"PROJECT"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def search_regex_insensitive(self, path: str, pattern: str) -> CommandOut:
        """Finds regex matches ignoring case in all files under 'path'. Returns file paths, line numbers, and content."""
        return self._execute_command(
            "rg",
            [
                "--ignore-case",
                "--line-number",
                "--column",
                "--no-heading",
                pattern,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "pattern": "*.py"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def find_files_by_glob(self, path: str, pattern: str) -> CommandOut:
        """Locates files matching a glob pattern (e.g., '*.py', '**/tests/*') under 'path'."""
        return self._execute_command(
            "rg",
            [
                "--files",
                "-g",
                pattern,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "pattern": "README"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def find_files_by_name(self, path: str, pattern: str) -> CommandOut:
        """Finds files whose names contain the specified substring under 'path'."""
        return self._execute_command(
            "rg",
            [
                "--files",
                "-g",
                f"*{pattern}*",
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case({"path": "."}, {**EXPECTED_SUCCESS}, files=_TEST_FILES),
        ]
    )
    def list_all_files(self, path: str) -> CommandOut:
        """Recursively lists all files under the specified 'path'."""
        return self._execute_command(
            "rg",
            [
                "--files",
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "extension": "json"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def find_files_by_extension(self, path: str, extension: str) -> CommandOut:
        """Lists files matching a specific extension (e.g., 'py', 'json') under 'path'."""
        ext = extension.lstrip(".")
        return self._execute_command(
            "rg",
            [
                "--files",
                "-g",
                f"*.{ext}",
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "query": "hello", "glob": "*.py"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def search_text_in_glob(self, path: str, query: str, glob: str) -> CommandOut:
        """Finds literal text matches only within files that match the specified glob pattern under 'path'."""
        return self._execute_command(
            "rg",
            [
                "--fixed-strings",
                "--line-number",
                "--column",
                "--no-heading",
                "-g",
                glob,
                query,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "query": "world"}, {**EXPECTED_SUCCESS}, files=_TEST_FILES
            ),
        ]
    )
    def find_files_containing(self, path: str, query: str) -> CommandOut:
        """Lists names of files that contain at least one literal match of the 'query' under 'path'."""
        return self._execute_command(
            "rg",
            [
                "--fixed-strings",
                "--files-with-matches",
                query,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            # rg should return all files and a returncode of 0.
            Case(
                {"path": ".", "query": "MISSING_TEXT"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
        ]
    )
    def find_files_not_containing(self, path: str, query: str) -> CommandOut:
        """Lists names of files that do NOT contain the specified literal 'query' under 'path'."""
        return self._execute_command(
            "rg",
            [
                "--fixed-strings",
                "--files-without-match",
                query,
                ".",
            ],
            path,
        )

    @tool(
        tests=[
            Case(
                {"path": ".", "query": "hello"}, {**EXPECTED_SUCCESS}, files=_TEST_FILES
            ),
        ]
    )
    def count_text_occurrences(self, path: str, query: str) -> CommandOut:
        """Returns a count of literal matches of 'query' per file under 'path'."""
        return self._execute_command(
            "rg",
            [
                "--fixed-strings",
                "--count-matches",
                query,
                ".",
            ],
            path,
        )
