"""
Storage compute backend for calculating storage usage metrics by creator.
"""

from django.db.models import BigIntegerField, Sum
from django.db.models.functions import Coalesce

from core.models import Item
from core.storage.storage_compute_backend import StorageComputeBackend


class CreatorStorageComputeBackend(StorageComputeBackend):
    """Storage compute backend for calculating storage usage metrics by creator."""

    def compute_storage_used(self, users):
        """
        Compute the total storage used by a set of users.
        """
        return Item.objects.filter(
            creator__in=users, hard_deleted_at__isnull=True, quota_excluded=False
        ).aggregate(
            total_size=Sum(
                Coalesce("size", "expected_size", output_field=BigIntegerField()), default=0
            )
        )["total_size"]
