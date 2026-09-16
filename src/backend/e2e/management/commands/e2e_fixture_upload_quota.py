"""Prepare an isolated, small storage quota for upload integration tests."""

from django.core.management.base import BaseCommand

from django_ltree.functions import NLevel

from core import models
from core.storage.cache import invalidate_storage_used_cache
from core.tasks.item import process_item_purge

from e2e.utils import get_or_create_e2e_user


class Command(BaseCommand):
    """Reset only the dedicated upload-quota test account."""

    def handle(self, *args, **options):
        user = get_or_create_e2e_user("upload-quota@example.com")
        for item in (
            models.Item.objects.filter(creator=user).alias(level=NLevel("path")).filter(level=1)
        ):
            if item.deleted_at is None:
                item.soft_delete()
            if item.hard_deleted_at is None:
                item.hard_delete()
            process_item_purge(item.pk)
        user.storage_limit_override = 1024
        user.save(update_fields=["storage_limit_override"])
        invalidate_storage_used_cache([user.pk])
        self.stdout.write("Upload test account ready (1024 bytes).")
