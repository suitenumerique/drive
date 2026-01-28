"""Test the mirror file task."""

from io import BytesIO
from unittest import mock

from django.core.files.storage import default_storage

import pytest

from core.tasks.storage import (
    MissingMirroringConfigurationError,
    get_mirror_s3_client,
    mirror_file,
)


def test_get_mirror_s3_client_no_config_should_raise_an_exception(settings):
    """Test get_mirror_s3_client without config should raise an exception."""
    settings.AWS_S3_MIRRORING_ACCESS_KEY_ID = None
    settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY = None
    settings.AWS_S3_MIRRORING_ENDPOINT_URL = None

    with pytest.raises(MissingMirroringConfigurationError):
        get_mirror_s3_client()


def test_mirror_no_file_s3_config_should_abort(settings, caplog):
    """Test that the mirror file task should abort if the S3 configuration is not set."""
    settings.AWS_S3_MIRRORING_ACCESS_KEY_ID = None
    settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY = None
    settings.AWS_S3_MIRRORING_ENDPOINT_URL = None

    with caplog.at_level("INFO", logger="core.tasks.storage"):
        result = mirror_file("test.txt")

        assert result is None
        assert (
            "Mirroring S3 bucket is not configured, skipping mirroring" in caplog.text
        )


def test_mirror_file(settings, caplog):
    """Test mirror file correctly configured."""

    settings.AWS_S3_MIRRORING_ACCESS_KEY_ID = "access_key_id"
    settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY = "secret_access_key"
    settings.AWS_S3_MIRRORING_ENDPOINT_URL = "endpoint_url"
    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    file_content = b"content to mirror"
    default_storage.save("test_mirror.txt", BytesIO(file_content))

    with (
        mock.patch(
            "core.tasks.storage.get_mirror_s3_client"
        ) as mock_get_mirror_s3_client,
        caplog.at_level("INFO", logger="core.tasks.storage"),
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client
        mirror_file("test_mirror.txt")

        mock_get_mirror_s3_client.assert_called_once()
        mock_mirror_s3_client.put_object.assert_called_once_with(
            Bucket="test_mirror",
            Key="test_mirror.txt",
            Body=mock.ANY,
        )

        assert (
            mock_mirror_s3_client.put_object.call_args[1]["Body"].read() == file_content
        )
        assert (
            "Starting mirror of file test_mirror.txt to bucket test_mirror"
            in caplog.text
        )
        assert (
            "Successfully mirrored file test_mirror.txt to bucket test_mirror"
            in caplog.text
        )
