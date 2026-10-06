"""Clean stale pending items that were never fully uploaded."""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Item, ItemUploadStateChoices

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Remove pending items older than a given threshold."""

    help = "Delete pending items that have been stuck for too long"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=48,
            help="Age threshold in hours (default: 48)",
        )

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(hours=options["hours"])

        item_ids = Item.objects.filter(
            upload_state=ItemUploadStateChoices.PENDING,
            created_at__lt=threshold,
            hard_deleted_at__isnull=True,
        ).values_list("pk", flat=True)

        count = 0
        failed = 0
        for item_id in item_ids.iterator():
            try:
                if not self._delete_if_still_pending(item_id):
                    continue
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("Failed to clean stale pending item %s", item_id)
                failed += 1
                continue
            count += 1

        self.stdout.write(f"Cleaned {count} stale pending item(s).")
        if failed:
            self.stderr.write(f"Failed to clean {failed} stale pending item(s).")

    @staticmethod
    def _delete_if_still_pending(item_id):
        """
        Delete the item under a lock, unless its upload ended since it was listed.
        Return whether it was deleted.
        """
        with transaction.atomic():
            item = (
                Item.objects.select_for_update()
                .filter(
                    pk=item_id,
                    upload_state=ItemUploadStateChoices.PENDING,
                    hard_deleted_at__isnull=True,
                )
                .first()
            )
            if item is None:
                return False

            # The item may already be in the trash, directly or through an ancestor
            if item.deleted_at is None and item.ancestors_deleted_at is None:
                item.soft_delete()
            item.delete()

        return True
