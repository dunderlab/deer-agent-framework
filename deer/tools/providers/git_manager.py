from dataclasses import dataclass
import shlex
from typing import List

from deer.tools import ToolProvider, tool
from deer.tools.schemas import CommandOut, Case

# NOTE: Intentionally untested. Every tool is a thin wrapper over git, with no own logic.

# --- Global Constants ---
MAX_TIMEOUT = 300
REJECTED = {"stdout": "", "stderr": str, "returncode": -1, "message": str}


def _failure(message: str) -> dict:
    """Helper to construct a standardized failure response."""
    return {"stdout": "", "stderr": message, "returncode": -1, "message": message}


@dataclass
class GitManager(ToolProvider):

    # def git(self, path: str, *args: str | int) -> CommandOut:
    def git(self, path: str, args: List[str], timeout_seconds: int = 60) -> CommandOut:
        binary = "git"

        path = path.strip()

        # 1. Validate path boundaries
        self.jailed_path(path)

        # 2. Validate timeout constraints
        if not 1 <= timeout_seconds <= MAX_TIMEOUT:
            return _failure(f"timeout_seconds must be between 1 and {MAX_TIMEOUT}.")

        # 3. Verify binary exists in environment
        try:
            self.check_command(binary)
        except Exception as e:
            return _failure(f"Environment error: {e}")

        if not "clone" in args:
            try:
                # Ejecutamos rev-parse para confirmar que hay un .git en algún nivel superior
                check_repo = self.run_command(
                    "git rev-parse --is-inside-work-tree", cwd=str(path)
                )
                if check_repo["returncode"] != 0:
                    return _failure(
                        f"The path '{path}' is not inside a git repository."
                    )
            except Exception as e:
                return _failure(f"Error verifying git repository: {e}")

        # 4. Execution
        try:
            safe_command = shlex.join([binary] + args)
            result = self.run_command(
                safe_command, cwd=path, timeout_seconds=timeout_seconds
            )
        except Exception as e:
            return _failure(f"Execution error: {e}")

        # 5. Response formatting
        exit_code = result.get("returncode", -1)
        status_message = (
            "Command completed successfully."
            if exit_code == 0
            else f"Command failed with exit code {exit_code}."
        )
        return {**result, "message": status_message}

    def mormalize_target(self, path, target):
        normalized_target = target.strip()
        path = self.sanitize_path(path)
        if path and target.startswith(path.strip() + "/"):
            normalized_target = target[len(path) + 1 :]
        return normalized_target

    @property
    def commands(self):
        return ["git"]

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {
                    "path": "a",
                    "repository_url": "https://github.com/dunderlab/deer-agent-framework.git",
                    "repository_name": "deer",
                },
                {
                    "stdout": str,
                    "stderr": str,
                    "returncode": 0,
                    "message": str,
                },
                dirs=["a"],
                expected_paths=["a/deer/"],
            ),
            Case(
                {
                    "path": "a\n",
                    "repository_url": "https://github.com/dunderlab/deer-agent-framework.git\n",
                    "repository_name": "deer",
                },
                {
                    "stdout": str,
                    "stderr": str,
                    "returncode": 0,
                    "message": str,
                },
                dirs=["a"],
                expected_paths=["a/deer/"],
            ),
        ],
    )
    def git_clone(
        self, path: str, repository_url: str, repository_name: str
    ) -> CommandOut:
        """Clones a remote Git repository into a specified folder name.
        Use this as the first step to initialize a project in the jail before performing any other git or file operations.
        """
        return self.git(
            path, ["clone", repository_url.strip(), repository_name.strip()]
        )

    @tool(modifies_state=True)
    def git_checkout(self, path: str, target: str) -> CommandOut:
        """Switches the repository to a specific branch, commit hash, or tag.
        Use this to move the HEAD to a specific version of the project before analysis or fixing.
        """
        # We use the same git helper. 'target' can be a branch name or a commit hash.
        return self.git(path, ["checkout", self.mormalize_target(path, target)])

    @tool()
    def git_status(self, path: str) -> CommandOut:
        """Provides a concise summary of working tree changes.
        Use this to verify which files are untracked, modified, or staged before proceeding with other git operations.
        """
        return self.git(path, ["status", "--short"])

    @tool()
    def git_current_branch(self, path: str) -> CommandOut:
        """Identifies the active branch.
        Crucial for ensuring changes are applied to the intended context, especially in multi-branch workflows.
        """
        return self.git(path, ["branch", "--show-current"])

    @tool()
    def git_log(self, path: str, max_count: int) -> CommandOut:
        """Retrieves a condensed history of recent commits.
        Useful for tracking project evolution or identifying specific revisions for inspection.
        """
        return self.git(
            path, ["--no-pager", "log", "--oneline", "--decorate", f"-n {max_count}"]
        )

    @tool()
    def git_diff(self, path: str, target: str) -> CommandOut:
        """Shows line-by-line differences in the working tree that have NOT been staged yet.
        Essential for reviewing edits before adding them."""
        return self.git(
            path,
            [
                "--no-pager",
                "diff",
                "--",
                self.mormalize_target(path, target),
            ],
        )

    @tool()
    def git_staged_diff(self, path: str, target: str) -> CommandOut:
        """Shows line-by-line differences for changes already in the staging area.
        Use this as a final verification before committing."""
        return self.git(
            path,
            [
                "--no-pager",
                "diff",
                "--cached",
                "--",
                self.mormalize_target(path, target),
            ],
        )

    @tool()
    def git_show(self, path: str, revision: str) -> CommandOut:
        """Provides a detailed view of a specific commit, including metadata and the full patch.
        Use this to audit past changes."""
        return self.git(path, ["--no-pager", "show", "--stat", "--patch", revision])

    @tool(modifies_state=True)
    def git_add(self, path: str, target: str) -> CommandOut:
        """Moves changes from the working tree to the staging area.
        This is a mandatory prerequisite for 'git_commit'."""

        return self.git(path, ["add", "--", self.mormalize_target(path, target)])

    @tool(modifies_state=True)
    def git_commit(self, path: str, message: str) -> CommandOut:
        """Records staged changes into the repository history.
        Fails if the staging area is empty or if no changes are detected."""
        return self.git(path, ["commit", "-m", shlex.quote(message)])

    @tool(modifies_state=True)
    def git_restore(self, path: str, target: str) -> CommandOut:
        """Reverts unstaged modifications in the working tree.
        IRREVERSIBLE for uncommitted data; use only to discard unwanted edits."""
        return self.git(path, ["restore", "--", self.mormalize_target(path, target)])
