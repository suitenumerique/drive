"""Test the mirror file task."""

from io import BytesIO
from unittest import mock
from uuid import uuid4

from django.core.files.storage import default_storage

import botocore
import pytest

from core.factories import MirrorItemTaskFactory
from core.models import ItemTypeChoices, MirrorItemTaskStatusChoices
from core.tasks.storage import (
    get_mirror_s3_client,
    mirror_file,
)

pytestmark = pytest.mark.django_db

# As the task is bound, we need to ignore this error.
# pylint: disable=no-value-for-parameter


@pytest.fixture(autouse=True)
def clear_get_mirror_s3_client_cache():
    """Clear the cache for get_mirror_s3_client."""
    get_mirror_s3_client.cache_clear()


def test_get_mirror_s3_client_no_config_should_return_none(settings):
    """Test get_mirror_s3_client without config should return None."""
    settings.AWS_S3_MIRRORING_ACCESS_KEY_ID = None
    settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY = None
    settings.AWS_S3_MIRRORING_ENDPOINT_URL = None

    assert get_mirror_s3_client() is None


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


def test_mirror_file_existing_record_not_existing(caplog):
    """Test mirror file mirror_item_task not existing."""

    mirror_item_task_id = uuid4()

    with (
        mock.patch(
            "core.tasks.storage.get_mirror_s3_client"
        ) as mock_get_mirror_s3_client,
        caplog.at_level("ERROR", logger="core.tasks.storage"),
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client
        mirror_file(mirror_item_task_id)

    assert f"Mirror task {mirror_item_task_id} does not exist" in caplog.text


def test_mirror_file_existing_record_not_in_pending_status(caplog):
    """Test mirror file mirror_item_task not in pending status."""

    mirror_item_task = MirrorItemTaskFactory(
        status=MirrorItemTaskStatusChoices.PROCESSING
    )

    with (
        mock.patch(
            "core.tasks.storage.get_mirror_s3_client"
        ) as mock_get_mirror_s3_client,
        caplog.at_level("INFO", logger="core.tasks.storage"),
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client
        mirror_file(mirror_item_task.id)

    assert (
        f"Mirror task {mirror_item_task.id} is not pending, skipping mirroring"
        in caplog.text
    )

    mirror_item_task.refresh_from_db()
    assert mirror_item_task.status == MirrorItemTaskStatusChoices.PROCESSING


def test_mirror_file(settings, caplog):
    """Test mirror file correctly configured."""
    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    mirror_item_task = MirrorItemTaskFactory(
        item__type=ItemTypeChoices.FILE,
        item__filename="test_mirror.txt",
        item__mimetype="text/plain",
        status=MirrorItemTaskStatusChoices.PENDING,
    )
    item = mirror_item_task.item

    file_content = b"content to mirror"
    default_storage.save(item.file_key, BytesIO(file_content))

    with (
        mock.patch(
            "core.tasks.storage.get_mirror_s3_client"
        ) as mock_get_mirror_s3_client,
        caplog.at_level("INFO", logger="core.tasks.storage"),
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client
        mirror_file(mirror_item_task.id)

        mock_get_mirror_s3_client.assert_called_once()
        mock_mirror_s3_client.put_object.assert_called_once_with(
            Bucket="test_mirror",
            Key=item.file_key,
            Body=mock.ANY,
            ContentType="text/plain",
            Metadata={},
        )
        mirror_item_task.refresh_from_db()
        assert mirror_item_task.status == MirrorItemTaskStatusChoices.COMPLETED
        assert (
            mock_mirror_s3_client.put_object.call_args[1]["Body"].read() == file_content
        )
        assert (
            f"Starting mirror of file {item.file_key} to bucket test_mirror"
            in caplog.text
        )
        assert (
            f"Successfully mirrored file {item.file_key} to bucket test_mirror"
            in caplog.text
        )


def test_mirror_files_retry(settings):
    """Test mirror_file retry mechanism."""

    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    mirror_item_task = MirrorItemTaskFactory(
        item__type=ItemTypeChoices.FILE,
        item__filename="test_mirror.txt",
        item__mimetype="text/plain",
        status=MirrorItemTaskStatusChoices.PENDING,
    )

    assert mirror_item_task.retries == 0

    with (
        mock.patch(
            "core.tasks.storage.get_mirror_s3_client"
        ) as mock_get_mirror_s3_client,
        pytest.raises(botocore.exceptions.ClientError),
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client
        # No file exists on the origin bucket, The task will fail
        mirror_file(mirror_item_task.id)

    mirror_item_task.refresh_from_db()

    assert mirror_item_task.status == MirrorItemTaskStatusChoices.PENDING
    assert mirror_item_task.retries == 1


def test_mirror_file_max_retries_exceeded(settings):
    """Test mirror_file with max retries exceeded should store the task as failed."""

    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    mirror_item_task = MirrorItemTaskFactory(
        item__type=ItemTypeChoices.FILE,
        item__filename="test_mirror.txt",
        item__mimetype="text/plain",
        status=MirrorItemTaskStatusChoices.PENDING,
    )

    with (
        mock.patch(
            "core.tasks.storage.get_mirror_s3_client"
        ) as mock_get_mirror_s3_client,
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client
        # No file exists on the origin bucket, The task will fail
        mirror_file.max_retries = 0
        mirror_file(mirror_item_task.id)

    mirror_item_task.refresh_from_db()

    assert mirror_item_task.status == MirrorItemTaskStatusChoices.FAILED
    assert (
        mirror_item_task.error_details
        == "An error occurred (404) when calling the HeadObject operation: Not Found"
    )
