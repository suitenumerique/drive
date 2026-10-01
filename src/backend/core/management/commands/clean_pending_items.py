"""Clean stale pending items that were never fully uploaded."""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Item, ItemUploadStateChoices

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Hard delete pending items older than a given threshold."""

    help = "Hard delete pending items that have been stuck for too long"

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
                # The item row is the only pointer to the stored object, so it is
                # left to purge_deleted_items which removes the object first.
                if not self._mark_as_hard_deleted(item_id):
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
    def _mark_as_hard_deleted(item_id):
        """
        Mark the item as hard deleted so that purge_deleted_items purges it. Return
        False if the upload ended or the item was deleted in the meantime.
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

            if item.deleted_at is None and item.ancestors_deleted_at is None:
                item.soft_delete()

            if item.deleted_at is not None:
                item.hard_delete()
            else:
                # In the trash through an ancestor only: hard_delete() refuses it
                item.hard_deleted_at = timezone.now()
                item.save(update_fields=["hard_deleted_at"])

        return True
