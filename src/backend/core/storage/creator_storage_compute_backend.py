"""
Storage compute backend for calculating storage usage metrics by creator.
"""

from django.db.models import BigIntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from core.models import Item
from core.storage.storage_compute_backend import StorageComputeBackend


class CreatorStorageComputeBackend(StorageComputeBackend):
    """Storage compute backend for calculating storage usage metrics by creator."""

    @staticmethod
    def _counted_items():
        """Return the items counted in the storage used."""
        return Item.objects.filter(hard_deleted_at__isnull=True, quota_excluded=False)

    def compute_storage_used(self, users):
        """
        Compute the total storage used by a set of users.
        """
        return (
            self._counted_items()
            .filter(creator__in=users)
            .aggregate(total_size=Sum("size", default=0))["total_size"]
        )

    def storage_used_expression(self):
        """Return the storage used by each user, to annotate a User queryset."""
        total = (
            self._counted_items()
            .filter(creator=OuterRef("pk"))
            .order_by()
            .values("creator")
            .annotate(total=Sum("size"))
            .values("total")
        )
        return Coalesce(Subquery(total), 0, output_field=BigIntegerField())
