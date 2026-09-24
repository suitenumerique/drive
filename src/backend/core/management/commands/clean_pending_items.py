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

        items = Item.objects.filter(
            upload_state=ItemUploadStateChoices.PENDING,
            created_at__lt=threshold,
            hard_deleted_at__isnull=True,
        )

        count = 0
        failed = 0
        for item in items.iterator():
            try:
                with transaction.atomic():
                    # The item may already be in the trash, directly or through an ancestor
                    if item.deleted_at is None and item.ancestors_deleted_at is None:
                        item.soft_delete()
                    item.delete()
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("Failed to clean stale pending item %s", item.pk)
                failed += 1
                continue
            count += 1

        self.stdout.write(f"Cleaned {count} stale pending item(s).")
        if failed:
            self.stderr.write(f"Failed to clean {failed} stale pending item(s).")
