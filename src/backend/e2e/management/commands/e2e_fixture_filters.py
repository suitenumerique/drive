"""E2E fixture filters."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core import factories, models

from e2e.utils import get_or_create_e2e_user


class Command(BaseCommand):
    """E2E fixture filters."""

    help = "Generates E2E filters fixtures."

    def _create_file(self, user, title, filename):
        """Create a ready file owned by the user at the root."""
        return factories.ItemFactory(
            title=title,
            type=models.ItemTypeChoices.FILE,
            creator=user,
            filename=filename,
            update_upload_state=models.ItemUploadStateChoices.READY,
            users=[(user, models.RoleChoices.OWNER)],
        )

    def handle(self, *args, **options):
        """E2E fixture filters."""
        user = get_or_create_e2e_user("drive@example.com")
        contact = factories.UserFactory(
            email="alice@example.com",
            full_name="Alice Doe",
            short_name="Alice",
            sub=None,
            language="en-us",
        )

        factories.ItemFactory(
            title="Filters folder",
            type=models.ItemTypeChoices.FOLDER,
            creator=user,
            users=[(user, models.RoleChoices.OWNER)],
        )
        self._create_file(user, "Quarterly report", "quarterly-report.pdf")
        self._create_file(user, "Holiday photo", "holiday-photo.png")

        shared = self._create_file(user, "Shared report", "shared-report.pdf")
        factories.UserItemAccessFactory(item=shared, user=contact, role=models.RoleChoices.READER)

        old = self._create_file(user, "Old report", "old-report.pdf")
        # updated_at is an auto_now field, bypass it with a queryset update.
        models.Item.objects.filter(pk=old.pk).update(updated_at=timezone.now() - timedelta(days=60))

        self.stdout.write("Filters fixtures created")
