from deer.tools import ToolProvider, tool
from deer.schema.io import CommandOut

from dataclasses import dataclass
import shlex


class GitManagerError(ValueError):
    pass


@dataclass
class GitManager(ToolProvider):

    def git(self, path: str, *args: str | int) -> CommandOut:
        quoted_args = " ".join(shlex.quote(str(arg)) for arg in args)
        return self.run_command(f"git {quoted_args}", cwd=path)

    @property
    def commands(self):
        return ["git"]

    @tool()
    def git_status(self, path: str) -> CommandOut:
        """Provides a concise summary of working tree changes. Use this to verify which files are untracked, modified, or staged before proceeding with other git operations."""
        return self.git(path, "status", "--short")

    @tool()
    def git_current_branch(self, path: str) -> CommandOut:
        """Identifies the active branch. Crucial for ensuring changes are applied to the intended context, especially in multi-branch workflows."""
        return self.git(path, "branch", "--show-current")

    @tool()
    def git_log(self, path: str, max_count: int) -> CommandOut:
        """Retrieves a condensed history of recent commits. Useful for tracking project evolution or identifying specific revisions for inspection."""
        return self.git(
            path, "log", "--oneline", "--decorate", f"--max-count={max_count}"
        )

    @tool()
    def git_diff(self, path: str, target: str) -> CommandOut:
        """Shows line-by-line differences in the working tree that have NOT been staged yet. Essential for reviewing edits before adding them."""
        return self.git(path, "diff", "--", target)

    @tool()
    def git_staged_diff(self, path: str, target: str) -> CommandOut:
        """Shows line-by-line differences for changes already in the staging area. Use this as a final verification before committing."""
        return self.git(path, "diff", "--cached", "--", target)

    @tool()
    def git_show(self, path: str, revision: str) -> CommandOut:
        """Provides a detailed view of a specific commit, including metadata and the full patch. Use this to audit past changes."""
        return self.git(path, "show", "--stat", "--patch", revision)

    @tool(modifies_state=True)
    def git_add(self, path: str, target: str) -> CommandOut:
        """Moves changes from the working tree to the staging area. This is a mandatory prerequisite for 'git_commit'."""
        return self.git(path, "add", "--", target)

    @tool(modifies_state=True)
    def git_commit(self, path: str, message: str) -> CommandOut:
        """Records staged changes into the repository history. Fails if the staging area is empty or if no changes are detected."""
        return self.git(path, "commit", "-m", message)

    @tool(modifies_state=True)
    def git_restore(self, path: str, target: str) -> CommandOut:
        """Reverts unstaged modifications in the working tree. IRREVERSIBLE for uncommitted data; use only to discard unwanted edits."""
        return self.git(path, "restore", "--", target)
