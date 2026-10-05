from dataclasses import dataclass
from pathlib import Path
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
        # 1. Resolvemos el path de ejecución a una ruta absoluta real y limpia
        abs_cwd = Path(self.jailed_path(path)).resolve()

        # Ejecutamos el comando pasando el path como string
        result = super()._execute_command(binary, args, str(abs_cwd), timeout_seconds)

        raw_output = result.get("stdout")
        if not raw_output:
            return result

        absolute_lines = []
        for line in raw_output.splitlines():

            # 1. Identificamos la ruta, esté o no acompañada de línea/columna
            if ":" in line:
                relative_to_cwd, separator, rest = line.partition(":")
            else:
                relative_to_cwd, separator, rest = line, "", ""

            # 2. Normalizamos la ruta SIEMPRE (ya sea un archivo solo o una línea de match)
            try:
                full_system_path = (abs_cwd / relative_to_cwd).resolve()
                jail_root = Path(self.jail).resolve()
                jail_relative_path = full_system_path.relative_to(jail_root)

                # Reconstruimos la línea manteniendo el separador y el resto si existían
                absolute_lines.append(f"{jail_relative_path}{separator}{rest}")
            except ValueError:
                # Si la ruta escapa del jail, devolvemos la línea original
                absolute_lines.append(line)

        # result["stdout"] = "\n".join(absolute_lines)
        result["stdout"] = "\n".join(absolute_lines) + ("\n" if absolute_lines else "")
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
        """Finds literal fixed-string matches in all files under 'path'. Returns file paths, line numbers, and content.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Finds text using PCRE2 regex patterns in all files under 'path'. Returns file paths, line numbers, and content.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Finds literal text matches ignoring case in all files under 'path'. Returns file paths, line numbers, and content.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Finds regex matches ignoring case in all files under 'path'. Returns file paths, line numbers, and content.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Locates files matching a glob pattern (e.g., '*.py', '**/tests/*') under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Finds files whose names contain the specified substring under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Recursively lists all files under the specified 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Lists files matching a specific extension (e.g., 'py', 'json') under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Finds literal text matches only within files that match the specified glob pattern under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
                {"path": ".", "query": "world"},
                {**EXPECTED_SUCCESS},
                files=_TEST_FILES,
            ),
            Case(
                {
                    "path": "src",
                    "query": "hello world",
                },
                {
                    "stdout": "src/main.py\n",
                    "stderr": "",
                    "returncode": 0,
                    "message": "Command completed successfully.",
                },
                files={
                    "src/main.py": "def hello():\n    print('hello world')",
                },
            ),
        ]
    )
    def find_files_containing(self, path: str, query: str) -> CommandOut:
        """Lists names of files that contain at least one literal match of the 'query' under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Lists names of files that do NOT contain the specified literal 'query' under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
        """Returns a count of literal matches of 'query' per file under 'path'.
        Returns paths relative to the root directory. Use exactly as returned."""
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
