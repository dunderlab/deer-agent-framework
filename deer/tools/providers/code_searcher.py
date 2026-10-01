import shlex
from dataclasses import dataclass

from deer.tools import ToolProvider, tool
from deer.tools.schemas import CommandOut, Case

# Constants moved outside to prevent NameError
EXPECTED_SUCCESS = {
    "stdout": str,
    "stderr": str,
    "returncode": 0,
    "message": str,
}


@dataclass
class CodeSearcher(ToolProvider):
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

    def _rg(self, path: str, *args: str) -> CommandOut:
        """Internal helper to execute ripgrep commands."""
        quoted_args = " ".join(shlex.quote(arg) for arg in args)
        return self.run_command(f"rg {quoted_args}", cwd=path)

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
        return self._rg(
            path,
            "--fixed-strings",
            "--line-number",
            "--column",
            "--no-heading",
            query,
            ".",
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
        return self._rg(path, "--line-number", "--column", "--no-heading", pattern, ".")

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
        return self._rg(
            path,
            "--fixed-strings",
            "--ignore-case",
            "--line-number",
            "--column",
            "--no-heading",
            query,
            ".",
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
        return self._rg(
            path,
            "--ignore-case",
            "--line-number",
            "--column",
            "--no-heading",
            pattern,
            ".",
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
        return self._rg(path, "--files", "-g", pattern, ".")

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
        return self._rg(path, "--files", "-g", f"*{pattern}*", ".")

    @tool(
        tests=[
            Case({"path": "."}, {**EXPECTED_SUCCESS}, files=_TEST_FILES),
        ]
    )
    def list_all_files(self, path: str) -> CommandOut:
        """Recursively lists all files under the specified 'path'."""
        return self._rg(path, "--files", ".")

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
        return self._rg(path, "--files", "-g", f"*.{ext}", ".")

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
        return self._rg(
            path,
            "--fixed-strings",
            "--line-number",
            "--column",
            "--no-heading",
            "-g",
            glob,
            query,
            ".",
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
        return self._rg(path, "--fixed-strings", "--files-with-matches", query, ".")

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
        return self._rg(path, "--fixed-strings", "--files-without-match", query, ".")

    @tool(
        tests=[
            Case(
                {"path": ".", "query": "hello"}, {**EXPECTED_SUCCESS}, files=_TEST_FILES
            ),
        ]
    )
    def count_text_occurrences(self, path: str, query: str) -> CommandOut:
        """Returns a count of literal matches of 'query' per file under 'path'."""
        return self._rg(path, "--fixed-strings", "--count-matches", query, ".")
