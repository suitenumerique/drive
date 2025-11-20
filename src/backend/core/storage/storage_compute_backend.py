"""Storage compute backend for calculating storage usage metrics."""

from abc import ABC, abstractmethod


class StorageComputeBackend(ABC):
    """Abstract base class for storage compute backends."""

    @abstractmethod
    def compute_storage_used(self, user):
        """
        Compute the storage used by a user.

        Args:
            user: The user instance to compute storage for.

        Returns:
            int: The storage used in bytes.
        """
