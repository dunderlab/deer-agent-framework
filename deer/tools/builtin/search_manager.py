from deer.tools import ToolProvider, tool
from deer.schema.io import CommandOut

from dataclasses import dataclass
import shlex


class SearchManagerError(ValueError):
    pass


@dataclass
class SearchManager(ToolProvider):

    def rg(self, path: str, *args: str | int) -> CommandOut:
        quoted_args = " ".join(shlex.quote(str(arg)) for arg in args)
        return self.run_command(f"rg {quoted_args}", cwd=path)

    @property
    def commands(self):
        return ["rg"]

    @tool()
    def search_text(self, path: str, query: str) -> CommandOut:
        """Performs a recursive, literal fixed-string search for the 'query' under the specified 'path'. Returns file paths, line numbers, and matching content."""
        return self.rg(
            path,
            "--fixed-strings",
            "--line-number",
            "--column",
            "--no-heading",
            query,
            ".",
        )

    @tool()
    def search_regex(self, path: str, pattern: str) -> CommandOut:
        """Executes a recursive regex search using PCRE2 syntax under the specified 'path'. Useful for complex pattern matching in codebases."""
        return self.rg(
            path,
            "--line-number",
            "--column",
            "--no-heading",
            pattern,
            ".",
        )

    @tool()
    def search_text_ignore_case(self, path: str, query: str) -> CommandOut:
        """Recursive literal search that ignores character casing. Ideal for finding references when the exact casing is uncertain."""
        return self.rg(
            path,
            "--fixed-strings",
            "--ignore-case",
            "--line-number",
            "--column",
            "--no-heading",
            query,
            ".",
        )

    @tool()
    def search_regex_ignore_case(self, path: str, pattern: str) -> CommandOut:
        """Recursive regex search that ignores character casing. Use this for broad pattern matching where casing is irrelevant."""
        return self.rg(
            path,
            "--ignore-case",
            "--line-number",
            "--column",
            "--no-heading",
            pattern,
            ".",
        )

    @tool()
    def find_files(self, path: str, pattern: str) -> CommandOut:
        """Locates files matching a glob pattern (e.g., '*.py', '**/tests/*'). Useful for mapping specific file types or directory structures."""
        return self.rg(path, "--files", "-g", pattern, ".")

    @tool()
    def search_file_names(self, path: str, pattern: str) -> CommandOut:
        """Finds files whose names contain the specified substring. A quick way to locate known files without knowing their full path."""
        return self.rg(path, "--files", "-g", f"*{pattern}*", ".")

    @tool()
    def list_files(self, path: str) -> CommandOut:
        """Recursively lists all tracked files under the specified 'path'. Use this for an exhaustive inventory of the environment."""
        return self.rg(path, "--files", ".")

    @tool()
    def search_by_extension(self, path: str, extension: str) -> CommandOut:
        """Filters and lists files by their file extension. Essential for isolating specific language sources or configuration files."""
        normalized_extension = extension.lstrip(".")
        return self.rg(path, "--files", "-g", f"*.{normalized_extension}", ".")

    @tool()
    def search_text_in_files(self, path: str, query: str, glob: str) -> CommandOut:
        """Recursive literal search restricted to files that match a specific glob pattern. Highly efficient for targeted code analysis."""
        return self.rg(
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

    @tool()
    def files_with_matches(self, path: str, query: str) -> CommandOut:
        """Lists only the names of files that contain at least one literal match of the 'query'. Useful for identifying affected files without raw content."""
        return self.rg(path, "--fixed-strings", "--files-with-matches", query, ".")

    @tool()
    def files_without_matches(self, path: str, query: str) -> CommandOut:
        """Identifies files that do NOT contain the specified literal 'query'. Useful for finding files missing required headers or configurations."""
        return self.rg(path, "--fixed-strings", "--files-without-match", query, ".")

    @tool()
    def count_matches(self, path: str, query: str) -> CommandOut:
        """Provides a breakdown of match frequencies per file. Use this to gauge the density of specific terms or patterns across the project."""
        return self.rg(path, "--fixed-strings", "--count-matches", query, ".")
