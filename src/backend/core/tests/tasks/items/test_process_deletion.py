"""Test the process deletion task."""

import logging
from io import BytesIO

from django.core.files.storage import default_storage

import pytest

from core import factories, models
from core.tasks.item import process_item_deletion
from core.utils.no_leak import sha256_16

pytestmark = pytest.mark.django_db


def test_process_item_deletion_not_hard_deleted(caplog):
    """Test the process deletion task when the item is not hard deleted."""
    item = factories.ItemFactory()
    with caplog.at_level(logging.ERROR):
        process_item_deletion(item.id)

    assert models.Item.objects.filter(id=item.id).exists()
    item.refresh_from_db()
    assert item.hard_deleted_at is None
    assert (
        "To process an item deletion, it must be hard deleted first."
        in caplog.records[0].message
    )


def test_process_item_deletion_item_does_not_exist(caplog):
    """Test the process deletion task when the item does not exist."""
    with caplog.at_level(logging.ERROR):
        process_item_deletion(1)

    assert "Item 1 does not exist" in caplog.records[0].message


def test_process_item_deletion_item_file_is_ready(caplog):
    """Test the process deletion task when the item file is ready."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="foo.txt",
    )
    item.soft_delete()
    item.hard_delete()
    default_storage.save(item.file_key, BytesIO(b"my prose"))

    with caplog.at_level(logging.INFO, logger="core.tasks.item"):
        process_item_deletion(item.id)
        assert item.file_key not in caplog.text
        assert sha256_16(item.file_key) in caplog.text

    assert not models.Item.objects.filter(id=item.id).exists()
    assert not default_storage.exists(item.file_key)


def test_process_item_deletion_item_folder_hard_deleted():
    """Test the process deletion task when the item folder is hard deleted."""
    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item.soft_delete()
    item.hard_delete()

    process_item_deletion(item.id)

    assert not models.Item.objects.filter(id=item.id).exists()


def test_process_item_deletion_in_cascade():
    """Test the process deletion task when the item folder is hard deleted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, creator=user, users=[user]
    )

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

    process_item_deletion(parent.id)

    assert models.Item.objects.all().count() == 0
    assert not default_storage.exists(child_file.file_key)
    assert not default_storage.exists(child2_file.file_key)


def test_process_item_deletion_item_subfolder_in_cascade():
    """Test the process deletion task when the item subfolder is hard deleted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, creator=user, users=[user]
    )

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
    parent.refresh_from_db()
    assert parent.numchild == 2

    child.soft_delete()
    child.hard_delete()

    assert models.Item.objects.all().count() == 5
    parent.refresh_from_db()
    assert parent.numchild == 1

    process_item_deletion(child.id)

    assert models.Item.objects.all().count() == 3
    assert not default_storage.exists(child_file.file_key)
    assert default_storage.exists(child2_file.file_key)
