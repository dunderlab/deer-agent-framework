import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(f"DEER.{__name__}")


class GitDirectoryManager:
    """Manages directory states using Git with a separate storage directory and centralized ignore patterns."""

    def __init__(
        self,
        target_dir: str | Path,
        storage_dir: Optional[str | Path] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        self.target_dir = Path(target_dir).resolve()
        self.target_dir.mkdir(parents=True, exist_ok=True)

        if storage_dir:
            self.storage_dir = Path(storage_dir).resolve()
            # Usamos git-dir y work-tree explícitos
            self.git_args = [
                f"--git-dir={self.storage_dir}",
                f"--work-tree={self.target_dir}",
            ]
        else:
            self.storage_dir = self.target_dir / ".git"
            self.git_args = []

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Verificar si el repositorio ya está inicializado
        head_file = self.storage_dir / "HEAD"
        if not head_file.exists():
            if storage_dir:
                # Inicializar repositorio bare y configurar el work-tree persistentemente
                subprocess.run(
                    ["git", f"--git-dir={self.storage_dir}", "init", "--bare"],
                    check=True,
                )
                subprocess.run(
                    [
                        "git",
                        f"--git-dir={self.storage_dir}",
                        "config",
                        "core.worktree",
                        str(self.target_dir),
                    ],
                    check=True,
                )
            else:
                subprocess.run(["git", "init"], cwd=self.target_dir, check=True)

            logger.info("Initialized Git repository at storage: %s", self.storage_dir)

        if ignore_patterns:
            self._update_exclude_file(ignore_patterns)

    def _update_exclude_file(self, patterns: List[str]) -> None:
        """Writes ignore patterns directly to Git's internal exclude file inside storage_dir."""
        info_dir = self.storage_dir / "info"
        info_dir.mkdir(exist_ok=True)
        exclude_path = info_dir / "exclude"

        existing_patterns = set()
        if exclude_path.exists():
            existing_patterns = set(
                exclude_path.read_text(encoding="utf-8").splitlines()
            )

        new_patterns = [p for p in patterns if p not in existing_patterns]
        if new_patterns:
            with open(exclude_path, "a", encoding="utf-8") as f:
                if existing_patterns and not exclude_path.read_text().endswith("\n"):
                    f.write("\n")
                f.write("\n".join(new_patterns) + "\n")
            logger.info("Added ignore patterns to Git exclude file: %s", new_patterns)

    def _run_git(self, args: List[str]) -> str:
        """Executes a git command with configured storage paths, handling stale locks."""
        cmd = ["git"] + self.git_args + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.target_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip()

            # Si el error es por un index.lock bloqueado, intentamos limpiarlo una vez y reintentar
            if "index.lock': File exists" in error_output:
                lock_file = self.storage_dir / "index.lock"
                if lock_file.exists():
                    # logger.warning(
                    #     "Stale index.lock found in storage. Removing: %s", lock_file
                    # )
                    try:
                        lock_file.unlink()
                        # Reintentar el comando tras eliminar el bloqueo
                        result = subprocess.run(
                            cmd,
                            cwd=self.target_dir,
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )
                        return result.stdout.strip()
                    except Exception as retry_err:
                        logger.error(
                            "Failed to retry git command after removing lock: %s",
                            retry_err,
                        )

            logger.error("Git command failed '%s': %s", " ".join(cmd), error_output)
            raise

    # def save_state(self, message: str) -> str:
    #     """Saves the current state as a Git commit using absolute paths."""
    #     try:
    #         # Forzar el add usando la ruta absoluta del work-tree para evitar problemas de contexto
    #         self._run_git(["add", "-A", str(self.target_dir)])
    #
    #         # Verificar si hay cambios pendientes
    #         status = self._run_git(["status", "--porcelain"])
    #         if not status:
    #             logger.info("No changes to save. Returning current HEAD commit hash.")
    #             return self._run_git(["rev-parse", "--short", "HEAD"])
    #
    #         # Hacer el commit
    #         self._run_git(["commit", "-m", message])
    #
    #         # Obtener el hash del commit
    #         commit_hash = self._run_git(["rev-parse", "--short", "HEAD"])
    #         logger.info("State saved successfully with commit: %s", commit_hash)
    #         return commit_hash
    #
    #     except Exception as e:
    #         logger.error("Failed to save state with message '%s': %s", message, e)
    #         raise

    def save_state(self, message: str) -> str:
        """Saves the current state as a Git commit using absolute paths."""
        try:
            # Forzar el add usando la ruta absoluta del work-tree
            self._run_git(["add", "-A", str(self.target_dir)])

            # Verificar si hay cambios pendientes
            status = self._run_git(["status", "--porcelain"])
            has_commits = self._has_any_commits()

            if not status:
                logger.info("No changes to save.")
                if not has_commits:
                    # Si el repositorio está totalmente vacío y no hay cambios,
                    # creamos el primer commit permitiendo un commit vacío para inicializar la historia.
                    self._run_git(["commit", "--allow-empty", "-m", message])

                return self._run_git(["rev-parse", "--short", "HEAD"])

            # Hacer el commit normal si hay cambios
            self._run_git(["commit", "-m", message])

            # Obtener el hash del commit
            commit_hash = self._run_git(["rev-parse", "--short", "HEAD"])
            logger.info("State saved successfully with commit: %s", commit_hash)
            return commit_hash

        except Exception as e:
            logger.error("Failed to save state with message '%s': %s", message, e)
            raise

    def _has_any_commits(self) -> bool:
        """Helper para verificar si el repositorio tiene al menos un commit."""
        try:
            self._run_git(["rev-parse", "--verify", "HEAD"])
            return True
        except subprocess.CalledProcessError:
            return False

    def get_states(self) -> str:
        """Lists the commit history."""
        states = self._run_git(["log", "--oneline"]).split("\n")
        return dict(line.split(" ", 1) for line in states[::-1])

    def restore_state(self, commit_hash: str) -> bool:
        """Restores the directory to a specific git commit. Returns False if the commit doesn't exist or fails."""
        try:
            logger.info("Restoring directory to commit: %s", commit_hash)

            # Si el commit no existe, git checkout fallará y lanzará una excepción
            self._run_git(["checkout", commit_hash, "--", "."])

            # Registrar la restauración como un nuevo commit en el historial
            self._run_git(["add", "-A", str(self.target_dir)])

            # Verificar si hay cambios antes de hacer commit
            status = self._run_git(["status", "--porcelain"])
            if status:
                self._run_git(["commit", "-m", f"Restored to {commit_hash}"])

            return True
        except Exception as e:
            logger.error("Could not restore state to commit '%s': %s", commit_hash, e)
            return False

    def rollback(self) -> str:
        commit_hash = list(self.get_states().keys())[-1]
        self.restore_state(commit_hash)
        return commit_hash
