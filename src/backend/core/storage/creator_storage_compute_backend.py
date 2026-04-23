"""
Storage compute backend for calculating storage usage metrics by creator.
"""

from django.db.models import Sum

from core.models import Item
from core.storage.storage_compute_backend import StorageComputeBackend


class CreatorStorageComputeBackend(StorageComputeBackend):
    """Storage compute backend for calculating storage usage metrics by creator."""

    def compute_storage_used(self, users):
        """
        Compute the total storage used by a set of users.
        """
        return Item.objects.filter(creator__in=users).aggregate(total_size=Sum("size", default=0))[
            "total_size"
        ]
