"""Garbage-collect blobs that lost their last reference beyond the grace period."""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Blob
from core.tasks.blob import gc_unreferenced_blob


class Command(BaseCommand):
    """Schedule the deletion of blobs unreferenced since longer than the grace period."""

    help = "Garbage-collect blobs unreferenced since longer than the grace period"

    def handle(self, *args, **options):
        """Queue one garbage-collection task per eligible blob."""
        cutoff = timezone.now() - timedelta(hours=settings.BLOB_UNREFERENCED_GRACE_HOURS)

        count = 0
        for blob_id in Blob.objects.filter(unreferenced_at__lte=cutoff).values_list(
            "id", flat=True
        ):
            gc_unreferenced_blob.delay(blob_id)
            count += 1

        self.stdout.write(f"Scheduled garbage collection of {count} unreferenced blob(s).")
