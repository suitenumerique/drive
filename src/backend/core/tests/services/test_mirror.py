"""Test the mirror services."""

from unittest import mock
from uuid import uuid4

import pytest

from core.factories import ItemFactory
from core.models import ItemTypeChoices, MirrorItemTask, MirrorItemTaskStatusChoices
from core.services.mirror import (
    mirror_file,
    mirror_item,
    mirror_item_from_file_key,
)

pytestmark = pytest.mark.django_db


def test_mirror_item_from_file_key():
    """Test the mirror item from file key service."""

    item = ItemFactory(
        filename="test.txt",
        type=ItemTypeChoices.FILE,
    )

    with mock.patch("core.services.mirror.mirror_item") as mock_mirror_item:
        mirror_item_from_file_key(item.file_key)

    mock_mirror_item.assert_called_once_with(item)


def test_mirror_item_from_file_key_invalid_file_key(caplog):
    """Test the mirror item from file key service with an invalid file key."""
    with caplog.at_level("ERROR", logger="core.services.mirror"):
        mirror_item_from_file_key("invalid/file/key")

    assert "File key invalid/file/key is not a valid item file key" in caplog.text


def test_mirror_item_from_file_key_item_not_found(caplog):
    """Test the mirror item from file key service with an item not found."""
    item_id = uuid4()
    with caplog.at_level("ERROR", logger="core.services.mirror"):
        mirror_item_from_file_key(f"item/{item_id}/test.txt")

    assert f"Item {item_id} does not exist" in caplog.text


def test_mirror_item_from_file_key_invalid_item_id(caplog):
    """Test the mirror item from file key service with an invalid item ID."""
    with caplog.at_level("ERROR", logger="core.services.mirror"):
        mirror_item_from_file_key("item/invalid/test.txt")

    assert "Item ID invalid is not a valid UUID" in caplog.text


def test_mirror_item():
    """Test the mirror item service."""

    item = ItemFactory(
        filename="test.txt",
        type=ItemTypeChoices.FILE,
    )

    with (
        mock.patch("core.services.mirror.get_mirror_s3_client", return_value=True),
        mock.patch.object(mirror_file, "delay") as mock_mirror_file,
    ):
        mirror_item(item)

    mirror_item_task = MirrorItemTask.objects.get(item=item)
    assert mirror_item_task.status == MirrorItemTaskStatusChoices.PENDING
    mock_mirror_file.assert_called_once_with(mirror_item_task.id)


def test_mirror_item_no_mirror_s3_client(caplog):
    """Test the mirror item service with no mirror S3 client."""

    item = ItemFactory()

    with caplog.at_level("INFO", logger="core.services.mirror"):
        mirror_item(item)

    assert "Mirroring S3 bucket is not configured, skipping mirroring" in caplog.text
