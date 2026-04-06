"""Purge hard deleted items."""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from core.models import Item
from core.tasks.item import process_item_purge


class Command(BaseCommand):
    """
    Purge hard deleted items (file in S3 and database object):
    - items marked as hard deleted in database
    - items marked as soft deleted and for which the trashbin retention period has expired
    """

    help = "Purge hard deleted items"

    def handle(self, *args, **options):
        """Browse purgeable items and synchronously run them through the item purge process."""

        is_hard_deleted = Q(hard_deleted_at__isnull=False)
        is_purgeable = Q(
            deleted_at__lte=timezone.now()
            - timedelta(days=settings.TRASHBIN_CUTOFF_DAYS + settings.PURGE_GRACE_DAYS)
        )

        count = 0
        for item_id in Item.objects.filter(is_hard_deleted | is_purgeable).values_list(
            "id", flat=True
        ):
            process_item_purge.delay(item_id)
            count += 1

        self.stdout.write(f"Purged {count} deleted item(s).")
