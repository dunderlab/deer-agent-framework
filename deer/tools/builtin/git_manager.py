from deer.tools import ToolProvider, tool, Return, CommandOut

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
        """Returns the short git status for a repository path inside the jail."""
        return self.git(path, "status", "--short")

    @tool()
    def git_current_branch(self, path: str) -> CommandOut:
        """Returns the current branch name for a repository path inside the jail."""
        return self.git(path, "branch", "--show-current")

    @tool()
    def git_log(self, path: str, max_count: int) -> CommandOut:
        """Returns the recent commit log for a repository path inside the jail."""
        return self.git(
            path, "log", "--oneline", "--decorate", f"--max-count={max_count}"
        )

    @tool()
    def git_diff(self, path: str, target: str) -> CommandOut:
        """Returns the unstaged diff for a target path inside a repository."""
        return self.git(path, "diff", "--", target)

    @tool()
    def git_staged_diff(self, path: str, target: str) -> CommandOut:
        """Returns the staged diff for a target path inside a repository."""
        return self.git(path, "diff", "--cached", "--", target)

    @tool()
    def git_show(self, path: str, revision: str) -> CommandOut:
        """Returns details for a git revision inside a repository path."""
        return self.git(path, "show", "--stat", "--patch", revision)

    @tool(modifies_state=True)
    def git_add(self, path: str, target: str) -> CommandOut:
        """Stages a target path inside a repository."""
        return self.git(path, "add", "--", target)

    @tool(modifies_state=True)
    def git_commit(self, path: str, message: str) -> CommandOut:
        """Creates a commit in a repository path with the provided message."""
        return self.git(path, "commit", "-m", message)

    @tool(modifies_state=True)
    def git_restore(self, path: str, target: str) -> CommandOut:
        """Restores unstaged changes for a target path inside a repository."""
        return self.git(path, "restore", "--", target)
