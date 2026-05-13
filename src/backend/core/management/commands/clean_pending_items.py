"""Clean stale pending items that were never fully uploaded."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Item, ItemUploadStateChoices
from core.tasks.item import process_item_purge


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
        for item in items.iterator():
            item.soft_delete()
            item.hard_delete()
            process_item_purge.delay(item.id)
            count += 1

        self.stdout.write(f"Cleaned {count} stale pending item(s).")
