"""Management command to trigger wopi configuration celery task."""

from django.core.management.base import BaseCommand

from wopi.tasks.configure_wopi import configure_wopi_clients


class Command(BaseCommand):
    """Management command to trigger wopi configuration celery task."""

    def handle(self, *args, **options):
        """Handle the command."""
        configure_wopi_clients.delay()
