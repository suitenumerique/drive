"""Tests for the clean_pending_items management command."""

from datetime import timedelta
from io import BytesIO, StringIO
from unittest import mock

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
    """Pending items older than the threshold should be hard deleted."""
    old_date = timezone.now() - timedelta(hours=49)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    # Backdate the item
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)

    call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.hard_deleted_at is not None


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

    # 8h threshold → item hard deleted
    call_command("clean_pending_items", "--hours=8")

    item.refresh_from_db()
    assert item.hard_deleted_at is not None


def test_clean_pending_items_already_soft_deleted():
    """Old pending items already in the trash should be hard deleted without error."""
    old_date = timezone.now() - timedelta(hours=49)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=old_date)
    item.soft_delete()

    call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.hard_deleted_at is not None


def test_clean_pending_items_ancestor_soft_deleted():
    """Old pending items whose parent is in the trash should be hard deleted without error."""
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

    item.refresh_from_db()
    assert item.hard_deleted_at is not None
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

    original_hard_delete = models.Item.hard_delete

    def hard_delete(self):
        if self.pk == failing.pk:
            raise RuntimeError("boom")
        return original_hard_delete(self)

    err = StringIO()
    with mock.patch.object(models.Item, "hard_delete", hard_delete):
        call_command("clean_pending_items", stderr=err)

    other.refresh_from_db()
    assert other.hard_deleted_at is not None
    assert "Failed to clean 1 stale pending item(s)." in err.getvalue()
    # The soft delete of the failing item was rolled back with the failed hard delete
    failing.refresh_from_db()
    assert failing.deleted_at is None
    assert failing.hard_deleted_at is None


def _stale_pending_file(**kwargs):
    """Create a pending file older than the default threshold."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="foo.txt",
        update_upload_state=models.ItemUploadStateChoices.PENDING,
        **kwargs,
    )
    models.Item.objects.filter(pk=item.pk).update(created_at=timezone.now() - timedelta(hours=49))
    return item


def test_clean_pending_items_removes_stored_object():
    """The object uploaded for an abandoned item should be removed by the purge."""
    item = _stale_pending_file()
    default_storage.save(item.file_key, BytesIO(b"abandoned"))
    assert default_storage.exists(item.file_key)

    call_command("clean_pending_items")
    call_command("purge_deleted_items")

    assert not default_storage.exists(item.file_key)
    assert not models.Item.objects.filter(pk=item.pk).exists()


def test_clean_pending_items_no_stored_object():
    """An item whose upload never started has no object and should still be purged."""
    item = _stale_pending_file()
    assert not default_storage.exists(item.file_key)

    err = StringIO()
    call_command("clean_pending_items", stderr=err)
    call_command("purge_deleted_items", stderr=err)

    assert not models.Item.objects.filter(pk=item.pk).exists()
    assert err.getvalue() == ""


def test_clean_pending_items_ancestor_soft_deleted_removes_stored_object():
    """The object of an item in the trash through its parent should be purged too."""
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = _stale_pending_file(parent=parent)
    default_storage.save(item.file_key, BytesIO(b"abandoned"))
    parent.soft_delete()

    call_command("clean_pending_items")
    call_command("purge_deleted_items")

    assert not default_storage.exists(item.file_key)
    assert not models.Item.objects.filter(pk=item.pk).exists()
    assert models.Item.objects.filter(pk=parent.pk).exists()


def test_clean_pending_items_keeps_item_until_purged():
    """
    The item is the only pointer to its stored object: it should stay in database,
    hard deleted, until purge_deleted_items has removed the object.
    """
    item = _stale_pending_file()
    default_storage.save(item.file_key, BytesIO(b"abandoned"))

    call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.deleted_at is not None
    assert item.hard_deleted_at is not None
    assert default_storage.exists(item.file_key)


def test_clean_pending_items_upload_ended_meanwhile():
    """An item whose upload ended after being listed should be left untouched."""
    item = _stale_pending_file()
    default_storage.save(item.file_key, BytesIO(b"finalized"))

    def end_upload_then_list(queryset, *args, **kwargs):
        item_ids = list(queryset)
        models.Item.objects.filter(pk=item.pk).update(
            upload_state=models.ItemUploadStateChoices.READY
        )
        return iter(item_ids)

    with mock.patch("django.db.models.query.QuerySet.iterator", end_upload_then_list):
        call_command("clean_pending_items")

    item.refresh_from_db()
    assert item.deleted_at is None
    assert item.hard_deleted_at is None
    assert default_storage.exists(item.file_key)
