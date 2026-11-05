"""Migrate legacy items to content-addressed blobs."""

from django.core.management.base import BaseCommand

from core.models import Item, ItemTypeChoices, ItemUploadStateChoices
from core.tasks.blob import migrate_item_to_blob


class Command(BaseCommand):
    """Queue the blob migration of legacy file items (historical item/<uuid>/<name> key)."""

    help = "Migrate legacy items to content-addressed blobs"

    def add_arguments(self, parser):
        """Add a --limit option to queue a batch instead of everything."""
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of items to queue in this run.",
        )

    def handle(self, *args, **options):
        """Queue one migration task per eligible item."""
        queryset = (
            Item.objects.filter(
                type=ItemTypeChoices.FILE,
                blob__isnull=True,
                deleted_at__isnull=True,
                hard_deleted_at__isnull=True,
                upload_state=ItemUploadStateChoices.READY,
            )
            .order_by("created_at")
            .values_list("id", flat=True)
        )
        if options["limit"]:
            queryset = queryset[: options["limit"]]

        count = 0
        for item_id in queryset.iterator():
            migrate_item_to_blob.delay(item_id)
            count += 1

        self.stdout.write(f"Queued blob migration of {count} item(s).")
