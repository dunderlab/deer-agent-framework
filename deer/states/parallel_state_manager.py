import os
import subprocess
import shutil
from typing import Dict, Any
from .base import BaseStateManager


class ParallelGitStateManager(BaseStateManager):
    """Concrete State Manager driven by an isolated, parallel Git architecture."""

    def __init__(self):
        self.workspace_path: str | None = None
        self.hidden_git_dir: str | None = None
        self.custom_env: Dict[str, str] = {}

    def set_reference_state(
        self, workspace_path: str, label: str = "checkpoint"
    ) -> Dict[str, Any]:
        """Initializes tracking if missing, and updates the reference state checkpoint."""
        try:
            self.workspace_path = os.path.abspath(workspace_path)
            self.hidden_git_dir = os.path.join(
                os.path.dirname(self.workspace_path),
                f".deer_parallel_state_engine-{os.path.basename(self.workspace_path)}",
            )

            self.custom_env = os.environ.copy()
            self.custom_env["GIT_DIR"] = self.hidden_git_dir
            self.custom_env["GIT_WORK_TREE"] = self.workspace_path

            is_new_repo = not os.path.exists(self.hidden_git_dir)
            if is_new_repo:
                os.makedirs(self.hidden_git_dir, exist_ok=True)
                subprocess.run(
                    ["git", "init"],
                    cwd=self.workspace_path,
                    env=self.custom_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.name", "deer-state-engine"],
                    cwd=self.workspace_path,
                    env=self.custom_env,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "engine@dunderlab.internal"],
                    cwd=self.workspace_path,
                    env=self.custom_env,
                    check=True,
                )

            subprocess.run(
                ["git", "add", "."],
                cwd=self.workspace_path,
                env=self.custom_env,
                check=True,
            )

            result = subprocess.run(
                ["git", "commit", "-m", label, "--allow-empty"],
                cwd=self.workspace_path,
                env=self.custom_env,
                capture_output=True,
                text=True,
            )

            msg_type = "Initialized and marked" if is_new_repo else "Updated"
            return {
                "success": True,
                "message": f"{msg_type} reference state successfully with label: '{label}'.",
                "stdout": result.stdout.strip(),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to lock reference state: {str(e)}",
            }

    def rollback_to_previous_state(self) -> Dict[str, Any]:
        """Executes a hard rollback to the last recorded checkpoint using the cached environment."""
        if (
            not self.hidden_git_dir
            or not os.path.exists(self.hidden_git_dir)
            or not self.workspace_path
        ):
            return {
                "success": False,
                "message": "Engine Error: No active reference state has been set yet.",
            }

        try:
            restore_result = subprocess.run(
                ["git", "restore", "."],
                cwd=self.workspace_path,
                env=self.custom_env,
                capture_output=True,
                text=True,
            )

            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=self.workspace_path,
                env=self.custom_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return {
                "success": restore_result.returncode == 0,
                "message": "Workspace successfully reverted to the previous clean reference checkpoint.",
                "stderr": restore_result.stderr.strip(),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Fatal failure during parallel rollback execution: {str(e)}",
            }

    def purge_engine(self) -> None:
        """Clears the hidden metadata index permanently from disk."""
        if self.hidden_git_dir and os.path.exists(self.hidden_git_dir):
            shutil.rmtree(self.hidden_git_dir, ignore_errors=True)
        self.workspace_path = None
        self.hidden_git_dir = None
        self.custom_env.clear()
