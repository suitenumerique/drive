"""Test the S3MirroringStorage class."""

from io import BytesIO
from unittest import mock

from core.storage.s3_mirroring_storage import S3MirroringStorage


def test_s3_mirroring_storage():
    """Test the S3MirroringStorage class."""
    storage = S3MirroringStorage()

    with mock.patch(
        "core.storage.s3_mirroring_storage.mirror_item_from_file_key"
    ) as mock_mirror_item_from_file_key:
        name = storage.save("test.txt", BytesIO(b"test"))

    mock_mirror_item_from_file_key.assert_called_once_with("test.txt")
    assert storage.exists("test.txt")
    assert name == "test.txt"
