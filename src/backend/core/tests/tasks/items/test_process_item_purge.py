"""Test the process item purge task."""

import logging
from datetime import timedelta
from io import BytesIO
from random import randint

from django.core.files.storage import default_storage
from django.utils import timezone

import pytest

from core import factories, models
from core.tasks.item import process_item_purge

pytestmark = pytest.mark.django_db


def test_process_item_purge_item_does_not_exist(caplog, django_assert_num_queries):
    """Test the process item purge task when the item does not exist."""
    with caplog.at_level(logging.ERROR), django_assert_num_queries(1):
        process_item_purge(1)

    assert "Item 1 does not exist" in caplog.records[0].message


def test_process_item_purge_neither_soft_nor_hard_deleted(caplog, django_assert_num_queries):
    """Test the process item purge task when the item is neither soft nor hard deleted."""
    item = factories.ItemFactory()
    with caplog.at_level(logging.INFO), django_assert_num_queries(1):
        process_item_purge(item.id)

    assert models.Item.objects.filter(id=item.id).exists()
    item.refresh_from_db()
    assert item.hard_deleted_at is None
    assert (
        f"Item {item.id!s} is not eligible for purge: item is not deleted"
        in caplog.records[1].message
    )


def test_process_item_purge_soft_deleted_not_purgeable(caplog, django_assert_num_queries, settings):
    """Test the process item purge task when the item is soft deleted but not purgeable."""
    settings.TRASHBIN_CUTOFF_DAYS = cutoff = randint(0, 50)
    settings.PURGE_GRACE_DAYS = grace = randint(0, 20)

    item = factories.ItemFactory(
        deleted_at=timezone.now() - timedelta(days=cutoff + grace - 1, hours=23, minutes=59)
    )
    with caplog.at_level(logging.INFO), django_assert_num_queries(1):
        process_item_purge(item.id)

    assert models.Item.objects.filter(id=item.id).exists()
    item.refresh_from_db()
    assert item.hard_deleted_at is None
    assert (
        f"Item {item.id!s} is not eligible for purge: soft-deleted but not past purge cutoff"
        in caplog.records[1].message
    )


def test_process_item_purge_soft_deleted_purgeable(settings):
    """Test the process item purge task when the item is soft deleted and purgeable."""

    settings.TRASHBIN_CUTOFF_DAYS = cutoff = randint(0, 50)
    settings.PURGE_GRACE_DAYS = grace = randint(0, 20)

    item = factories.ItemFactory(
        deleted_at=timezone.now() - timedelta(days=cutoff + grace),
        type=models.ItemTypeChoices.FILE,
        filename="foo.txt",
    )

    default_storage.save(item.file_key, BytesIO(b"my prose"))
    assert default_storage.exists(item.file_key)

    process_item_purge(item.id)

    assert not models.Item.objects.filter(id=item.id).exists()
    assert not default_storage.exists(item.file_key)


def test_process_item_purge_item_file_is_ready():
    """Test the process item purge task when the item file is ready."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="foo.txt",
    )
    item.soft_delete()
    item.hard_delete()
    default_storage.save(item.file_key, BytesIO(b"my prose"))
    assert default_storage.exists(item.file_key)

    process_item_purge(item.id)

    assert not models.Item.objects.filter(id=item.id).exists()
    assert not default_storage.exists(item.file_key)


def test_process_item_purge_item_folder_hard_deleted():
    """Test the process item purge task when the item folder is hard deleted."""
    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item.soft_delete()
    item.hard_delete()

    process_item_purge(item.id)

    assert not models.Item.objects.filter(id=item.id).exists()


def test_process_item_purge_in_cascade():
    """Test the process item purge task when the item folder is hard deleted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, creator=user, users=[user])

    child = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, parent=parent, creator=user, users=[user]
    )
    child2 = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, parent=parent, creator=user, users=[user]
    )

    child_file = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=child,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    child2_file = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=child2,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    default_storage.save(child_file.file_key, BytesIO(b"my prose"))
    default_storage.save(child2_file.file_key, BytesIO(b"my prose"))

    parent.soft_delete()
    parent.hard_delete()

    assert models.Item.objects.all().count() == 5

    process_item_purge(parent.id)

    assert models.Item.objects.all().count() == 0
    assert not default_storage.exists(child_file.file_key)
    assert not default_storage.exists(child2_file.file_key)


def test_process_item_purge_item_subfolder_in_cascade():
    """Test the process item purge task when the item subfolder is hard deleted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, creator=user, users=[user])

    child = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, parent=parent, creator=user, users=[user]
    )
    child2 = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, parent=parent, creator=user, users=[user]
    )

    child_file = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=child,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    child2_file = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=child2,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    default_storage.save(child_file.file_key, BytesIO(b"my prose"))
    default_storage.save(child2_file.file_key, BytesIO(b"my prose"))

    child.soft_delete()
    child.hard_delete()

    assert models.Item.objects.all().count() == 5

    process_item_purge(child.id)

    assert models.Item.objects.all().count() == 3
    assert not default_storage.exists(child_file.file_key)
    assert default_storage.exists(child2_file.file_key)


def test_process_item_purge_file_missing_from_storage():
    """The process should not crash if file is already missing."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="foo.txt",
    )
    # Do NOT create any file

    item.soft_delete()
    item.hard_delete()

    process_item_purge(item.id)

    assert not models.Item.objects.filter(id=item.id).exists()


def test_process_item_purge_stops_on_subfolder_delete_failure(monkeypatch):
    """If a delete fails, the purge must stop immediately and log an error."""

    user = factories.UserFactory()

    root = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        creator=user,
        users=[user],
    )
    subfolder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        parent=root,
        creator=user,
        users=[user],
    )

    file1 = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=subfolder,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    file2 = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=subfolder,
        creator=user,
        users=[user],
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    default_storage.save(file1.file_key, BytesIO(b"file1"))
    default_storage.save(file2.file_key, BytesIO(b"file2"))

    root.soft_delete()
    root.hard_delete()

    original_delete = models.Item.delete

    def failing_delete(self, *args, **kwargs):
        if self.id == subfolder.id:
            raise RuntimeError("Simulated failure on subfolder delete")
        return original_delete(self, *args, **kwargs)

    monkeypatch.setattr(models.Item, "delete", failing_delete)

    # The process should raise and stop immediately
    with pytest.raises(RuntimeError) as exc_info:
        process_item_purge(root.id)

    # Subfolder and folder should still exist
    assert "Simulated failure on subfolder delete" in str(exc_info.value)
    assert models.Item.objects.filter(id=subfolder.id).exists()
    assert models.Item.objects.filter(id=root.id).exists()

    # The files should have processed first and should be deleted
    assert not default_storage.exists(file1.file_key)
    assert not default_storage.exists(file2.file_key)
