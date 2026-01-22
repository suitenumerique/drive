"""Test the S3MirroringStorage class."""

from io import BytesIO
from unittest.mock import patch

from core.storage.s3_mirroring_storage import S3MirroringStorage, mirror_file


def test_s3_mirroring_storage():
    """Test the S3MirroringStorage class."""
    storage = S3MirroringStorage()

    with patch.object(mirror_file, "delay") as mock_mirror_file:
        name = storage.save("test.txt", BytesIO(b"test"))

    mock_mirror_file.assert_called_once_with("test.txt")
    assert storage.exists("test.txt")
    assert name == "test.txt"
