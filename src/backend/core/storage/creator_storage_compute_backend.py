"""
Storage compute backend for calculating storage usage metrics by creator.
"""

from django.db.models import Sum

from core.models import Item
from core.storage.storage_compute_backend import StorageComputeBackend


class CreatorStorageComputeBackend(StorageComputeBackend):
    """Storage compute backend for calculating storage usage metrics by creator."""

    def compute_storage_used(self, user):
        """
        Compute the storage used by a user.
        """
        return Item.objects.filter(creator=user).aggregate(
            total_size=Sum("size", default=0)
        )["total_size"]
