"""Update suspicious item file hash"""

from django.core.management.base import BaseCommand

from core.models import Item, ItemUploadStateChoices
from core.tasks.item import update_suspicious_item_file_hash


class Command(BaseCommand):
    """Update suspicious item file hash command"""

    help = "Update suspicious item file hash"

    def handle(self, *args, **options):
        """Update suspicious item file hash"""
        self.stdout.write("Starting update suspicious item file hash command")
        items = Item.objects.filter(
            upload_state=ItemUploadStateChoices.SUSPICIOUS,
            malware_detection_info__file_hash__isnull=True,
        ).iterator()

        for item in items:
            self.stdout.write(
                f"Triggering update suspicious item file hash for item {item.id}"
            )
            update_suspicious_item_file_hash.delay(item.id)
        self.stdout.write("Update suspicious item file hash command completed")
