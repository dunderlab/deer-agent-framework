from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseStateManager(ABC):
    """Abstract Base Class enforcing a strict 3-function transactional contract.

    Integrates initialization and checkpointing into a single call, exposing
    state locking, state restoration, and engine purging capabilities.
    """

    @abstractmethod
    def set_reference_state(
        self, workspace_path: str, label: str = "checkpoint"
    ) -> Dict[str, Any]:
        """Freezes or updates a targeted directory state.

        Requirement 1 & 2: If the underlying engine tracking infrastructure for
        this path already exists, it preserves history and updates the baseline.
        Otherwise, it initializes the tracking layer dynamically on the fly.

        Args:
            workspace_path (str): The target physical directory to freeze.
            label (str): A unique identifier or description for this state commit.

        Returns:
            Dict[str, Any]: Status dictionary with 'success' (bool) and 'message' (str).
        """
        pass

    @abstractmethod
    def rollback_to_previous_state(self) -> Dict[str, Any]:
        """Restores the workspace back to the last marked reference state.

        Requirement 4: Discards mutations, rewrites original file contents from
        the hidden engine metadata, and purges untracked pollution from disk.

        Returns:
            Dict[str, Any]: Status dictionary with 'success' (bool) and 'message' (str).
        """
        pass

    @abstractmethod
    def purge_engine(self) -> None:
        """Completely obliterates all dynamic tracking records, logs, and metadata.

        Closes the manager layer and leaves the workspace clean without any
        footprints or framework traces behind.
        """
        pass
