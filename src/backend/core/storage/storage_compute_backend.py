"""Storage compute backend for calculating storage usage metrics."""

from abc import ABC, abstractmethod


class StorageComputeBackend(ABC):
    """Abstract base class for storage compute backends."""

    @abstractmethod
    def compute_storage_used(self, users):
        """
        Compute the total storage used by a set of users.

        Args:
            users: A QuerySet of user instances.

        Returns:
            int: The total storage used in bytes.
        """
