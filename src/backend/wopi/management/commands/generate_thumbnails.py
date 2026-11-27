"""Management command to queue thumbnail generation for existing files."""

from django.core.management.base import BaseCommand, CommandError

from core import models
from wopi.conversion.thumbnails import thumbnail_clients
from wopi.tasks.configure_wopi import configure_wopi_clients
from wopi.tasks.thumbnails import generate_item_thumbnail


class Command(BaseCommand):
    """Queue thumbnail generation for every ready file."""

    def handle(self, *args, **options):
        """Handle the command."""
        if not any(thumbnail_clients()):
            raise CommandError("No WOPI client defines a ThumbnailServiceUrl option.")

        # The renders need the formats each client lists, which a configuration cached
        # by an earlier version does not record.
        configure_wopi_clients()

        items = models.Item.objects.filter(
            type=models.ItemTypeChoices.FILE,
            upload_state=models.ItemUploadStateChoices.READY,
            deleted_at__isnull=True,
        ).values_list("id", flat=True)

        for item_id in items.iterator():
            generate_item_thumbnail.delay(str(item_id))
