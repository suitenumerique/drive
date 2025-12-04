"""Test the update_suspicious_item_file_hash task"""

from io import BytesIO

from django.core.files.storage import default_storage

import pytest

from core.factories import ItemFactory
from core.models import ItemTypeChoices, ItemUploadStateChoices
from core.tasks.item import update_suspicious_item_file_hash

pytestmark = pytest.mark.django_db


def test_update_suspicious_item_file_hash_item_does_not_exist(caplog):
    """Test the update_suspicious_item_file_hash task when the item does not exist"""
    with caplog.at_level("ERROR", logger="core.tasks.item"):
        update_suspicious_item_file_hash(1)
        assert (
            "updating suspicious item file hash: Item 1 does not exist" in caplog.text
        )


def test_update_suspicious_item_file_hash_item_not_suspicious(caplog):
    """Test the update_suspicious_item_file_hash task when the item is not suspicious"""
    item = ItemFactory(update_upload_state=ItemUploadStateChoices.READY)
    with caplog.at_level("ERROR", logger="core.tasks.item"):
        update_suspicious_item_file_hash(item.id)
        assert (
            f"updating suspicious item file hash: Item {item.id} is not suspicious"
            in caplog.text
        )


def test_update_suspicious_item_file_hash_item_suspicious():
    """Test the update_suspicious_item_file_hash task when the item is suspicious"""
    item = ItemFactory(
        update_upload_state=ItemUploadStateChoices.SUSPICIOUS,
        type=ItemTypeChoices.FILE,
        filename="test.txt",
    )
    default_storage.save(item.file_key, BytesIO(b"my prose"))

    assert "file_hash" not in item.malware_detection_info

    update_suspicious_item_file_hash(item.id)
    item.refresh_from_db()
    assert item.malware_detection_info["file_hash"] is not None
