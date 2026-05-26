from deer.tools import ToolProvider, tool, Return

from dataclasses import dataclass
from pathlib import Path
import shlex


class SearchManagerError(ValueError):
    pass


CommandOut = Return(stdout=str, stderr=str, returncode=int)


@dataclass
class SearchManager(ToolProvider):
    jail: Path | str

    def __post_init__(self):
        # Resolve the jail to an absolute, real path immediately.
        # strict=True ensures the base jail directory actually exists.
        self.jail = Path(self.jail).resolve(strict=True)

    def rg(self, path: str, *args: str | int) -> CommandOut:
        quoted_args = " ".join(shlex.quote(str(arg)) for arg in args)
        return self.run_command(f"rg {quoted_args}", cwd=path)

    @tool()
    def search_text(self, path: str, query: str) -> CommandOut:
        """Searches for literal text under a path inside the jail."""
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
        """Searches for a regex pattern under a path inside the jail."""
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
        """Searches for literal text case-insensitively under a path inside the jail."""
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
        """Searches for a regex pattern case-insensitively under a path inside the jail."""
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
        """Finds files matching a glob pattern under a path inside the jail."""
        return self.rg(path, "--files", "-g", pattern, ".")

    @tool()
    def search_file_names(self, path: str, pattern: str) -> CommandOut:
        """Finds files whose names contain text under a path inside the jail."""
        return self.rg(path, "--files", "-g", f"*{pattern}*", ".")

    @tool()
    def list_files(self, path: str) -> CommandOut:
        """Lists files under a path inside the jail."""
        return self.rg(path, "--files", ".")

    @tool()
    def search_by_extension(self, path: str, extension: str) -> CommandOut:
        """Lists files with an extension under a path inside the jail."""
        normalized_extension = extension.lstrip(".")
        return self.rg(path, "--files", "-g", f"*.{normalized_extension}", ".")

    @tool()
    def search_text_in_files(self, path: str, query: str, glob: str) -> CommandOut:
        """Searches for literal text under a path, restricted to files matching a glob."""
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
        """Lists files containing literal text under a path inside the jail."""
        return self.rg(path, "--fixed-strings", "--files-with-matches", query, ".")

    @tool()
    def files_without_matches(self, path: str, query: str) -> CommandOut:
        """Lists files that do not contain literal text under a path inside the jail."""
        return self.rg(path, "--fixed-strings", "--files-without-match", query, ".")

    @tool()
    def count_matches(self, path: str, query: str) -> CommandOut:
        """Counts literal text matches per file under a path inside the jail."""
        return self.rg(path, "--fixed-strings", "--count-matches", query, ".")
