"""Tests for the clean_pending_items management command."""

from datetime import timedelta
from unittest import mock

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


def test_clean_pending_items_already_soft_deleted():
    """Old pending items already in the trash should be deleted without error."""
    old_date = timezone.now() - timedelta(hours=49)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)
    item.soft_delete()

    call_command("clean_pending_items")

    assert not models.Item.objects.filter(pk=item.pk).exists()


def test_clean_pending_items_ancestor_soft_deleted():
    """Old pending items whose parent is in the trash should be deleted without error."""
    old_date = timezone.now() - timedelta(hours=49)
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)
    parent.soft_delete()

    call_command("clean_pending_items")

    assert not models.Item.objects.filter(pk=item.pk).exists()
    assert models.Item.objects.filter(pk=parent.pk).exists()


def test_clean_pending_items_failure_does_not_stop_others():
    """A failure on one item is rolled back and the other items are still cleaned."""
    old_date = timezone.now() - timedelta(hours=49)
    items = factories.ItemFactory.create_batch(
        2,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk__in=[i.pk for i in items]).update(created_at=old_date)
    failing, other = items

    original_delete = models.Item.delete

    def delete(self, *args, **kwargs):
        if self.pk == failing.pk:
            raise RuntimeError("boom")
        return original_delete(self, *args, **kwargs)

    with mock.patch.object(models.Item, "delete", delete):
        call_command("clean_pending_items")

    assert not models.Item.objects.filter(pk=other.pk).exists()
    # The soft delete of the failing item was rolled back with the failed delete
    failing.refresh_from_db()
    assert failing.deleted_at is None
