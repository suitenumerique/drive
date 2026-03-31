"""Test the duplicate_file_on_mirroring_bucket task."""

from unittest import mock

import botocore
import pytest

from core.factories import ItemFactory
from core.models import ItemTypeChoices, MirrorItemTask, MirrorItemTaskStatusChoices
from core.tasks.storage import duplicate_file_on_mirroring_bucket

pytestmark = pytest.mark.django_db


def test_duplicate_file_no_s3_config_should_abort(settings, caplog):
    """Task should abort and log when mirroring S3 is not configured."""
    settings.AWS_S3_MIRRORING_ACCESS_KEY_ID = None
    settings.AWS_S3_MIRRORING_SECRET_ACCESS_KEY = None
    settings.AWS_S3_MIRRORING_ENDPOINT_URL = None

    with caplog.at_level("INFO", logger="core.tasks.storage"):
        duplicate_file_on_mirroring_bucket("item-id", "old/key", "new/key")

    assert (
        "Mirroring S3 bucket is not configured, skipping renaming file on the mirroring bucket"
        in caplog.text
    )


def test_duplicate_file_source_not_found_on_mirror_should_trigger_mirror_file(settings):
    """When the source file does not exist on the mirroring bucket, mirror it instead."""
    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    item = ItemFactory(type=ItemTypeChoices.FILE, filename="file.txt")

    client_error = botocore.exceptions.ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )

    with (
        mock.patch("core.tasks.storage.get_mirror_s3_client") as mock_get_mirror_s3_client,
        mock.patch("core.tasks.storage.mirror_file") as mock_mirror_file,
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_mirror_s3_client.head_object.side_effect = client_error
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client

        duplicate_file_on_mirroring_bucket(item.pk, "old/key", "new/key")

        mock_mirror_s3_client.head_object.assert_called_once_with(
            Bucket="test_mirror", Key="old/key"
        )

        mirror_task = MirrorItemTask.objects.get(item=item)
        assert mirror_task.status == MirrorItemTaskStatusChoices.PENDING

        mock_mirror_file.delay.assert_called_once_with(mirror_task.id)

        mock_mirror_s3_client.copy_object.assert_not_called()


def test_duplicate_file_source_exists_should_copy_without_delete(settings):
    """
    When the source file exists on the mirroring bucket, copy it without deleting the original.
    """
    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    item = ItemFactory(type=ItemTypeChoices.FILE, filename="file.txt")

    with (
        mock.patch("core.tasks.storage.get_mirror_s3_client") as mock_get_mirror_s3_client,
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_mirror_s3_client.head_object.return_value = {"ContentLength": 42}
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client

        duplicate_file_on_mirroring_bucket(item.pk, "old/key", "new/key")

        mock_mirror_s3_client.head_object.assert_called_once_with(
            Bucket="test_mirror", Key="old/key"
        )
        mock_mirror_s3_client.copy_object.assert_called_once_with(
            Bucket="test_mirror",
            CopySource={"Bucket": "test_mirror", "Key": "old/key"},
            Key="new/key",
            MetadataDirective="COPY",
        )
        mock_mirror_s3_client.delete_object.assert_not_called()


def test_duplicate_file_source_exists_does_not_create_mirror_task(settings):
    """When the source file exists on the mirroring bucket, no MirrorItemTask should be created."""
    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    item = ItemFactory(type=ItemTypeChoices.FILE, filename="file.txt")

    with mock.patch("core.tasks.storage.get_mirror_s3_client") as mock_get_mirror_s3_client:
        mock_mirror_s3_client = mock.MagicMock()
        mock_mirror_s3_client.head_object.return_value = {"ContentLength": 42}
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client

        duplicate_file_on_mirroring_bucket(item.pk, "old/key", "new/key")

    assert not MirrorItemTask.objects.filter(item=item).exists()


def test_duplicate_file_source_not_found_creates_exactly_one_mirror_task(settings):
    """Only one MirrorItemTask should be created when the source file is missing."""
    settings.AWS_S3_MIRRORING_STORAGE_BUCKET_NAME = "test_mirror"

    item = ItemFactory(type=ItemTypeChoices.FILE, filename="file.txt")

    client_error = botocore.exceptions.ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )

    with (
        mock.patch("core.tasks.storage.get_mirror_s3_client") as mock_get_mirror_s3_client,
        mock.patch("core.tasks.storage.mirror_file"),
    ):
        mock_mirror_s3_client = mock.MagicMock()
        mock_mirror_s3_client.head_object.side_effect = client_error
        mock_get_mirror_s3_client.return_value = mock_mirror_s3_client

        duplicate_file_on_mirroring_bucket(item.pk, "old/key", "new/key")

    assert MirrorItemTask.objects.filter(item=item).count() == 1
