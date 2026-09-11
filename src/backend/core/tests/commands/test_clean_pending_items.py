"""Tests for the clean_pending_items management command."""

from datetime import timedelta
from io import BytesIO

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_clean_pending_items_no_stale_items():
    """Nothing happens when there are no stale pending items."""
    call_command("clean_pending_items")


def test_clean_pending_items_recent_pending_not_deleted():
    """Recent pending items (within threshold) should not be deleted."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )

    call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.deleted_at is None


def test_clean_pending_items_old_pending_deleted():
    """Pending items older than the threshold should be deleted."""
    old_date = timezone.now() - timedelta(hours=49)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    # Backdate the item
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)

    call_command("clean_pending_items")

    assert not models.Item.objects.filter(pk=item.pk).exists()


def test_clean_pending_items_old_non_pending_not_deleted():
    """Old items that are not pending should not be deleted."""
    old_date = timezone.now() - timedelta(hours=49)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)

    call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.deleted_at is None
    assert item.hard_deleted_at is None


def test_clean_pending_items_custom_hours():
    """The --hours argument controls the age threshold."""
    old_date = timezone.now() - timedelta(hours=10)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)

    # Default 48h threshold → item not deleted
    call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.deleted_at is None

    # 8h threshold → item deleted
    call_command("clean_pending_items", "--hours=8")

    assert not models.Item.objects.filter(pk=item.pk).exists()


def test_clean_pending_items_removes_orphan_file_from_storage():
    """Stale pending items must also have their storage file removed."""
    old_date = timezone.now() - timedelta(hours=49)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="pending.txt",
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)
    default_storage.save(item.file_key, BytesIO(b"orphan data"))

    call_command("clean_pending_items")

    assert not models.Item.objects.filter(pk=item.pk).exists()
    assert not default_storage.exists(item.file_key)
