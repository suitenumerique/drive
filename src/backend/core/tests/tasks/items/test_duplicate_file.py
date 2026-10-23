"""Module for the tests related to the duplicate_file celery task."""

import uuid
from io import BytesIO
from unittest import mock

from django.core.files.storage import default_storage

import botocore
import pytest

from core import factories, models
from core.tasks.item import duplicate_file

pytestmark = pytest.mark.django_db

# As the task is bound, we need to ignore this error.
# pylint: disable=no-value-for-parameter


def test_duplicate_file_item_to_duplicate_does_not_exist(console_logs):
    """Test when the item_to_duplicate does not exists, should abort the task."""

    item_to_duplicate_id = uuid.uuid4()
    duplicate_file(item_to_duplicate_id=item_to_duplicate_id, duplicated_item_id=uuid.uuid4())

    assert console_logs == [
        {
            "event": (
                f"duplicating file: item_to_duplicate with id {item_to_duplicate_id} does not"
                " exist, aborting"
            ),
            "level": "error",
            "logger": "core.tasks.item",
            "exception": mock.ANY,
        }
    ]


def test_duplicate_file_duplicated_item_does_not_exist(console_logs):
    """Test when the duplicated_item does not exists, should abort the task."""

    item_to_duplicate = factories.ItemFactory(type=models.ItemTypeChoices.FILE)
    console_logs.clear()

    duplicated_item_id = uuid.uuid4()
    duplicate_file(
        item_to_duplicate_id=item_to_duplicate.id,
        duplicated_item_id=duplicated_item_id,
    )

    assert console_logs == [
        {
            "event": (
                f"duplicating file: duplicated_item with id {duplicated_item_id} does not exist,"
                " aborting"
            ),
            "level": "error",
            "logger": "core.tasks.item",
            "exception": mock.ANY,
        }
    ]


def test_duplicate_file_duplicated_file_not_in_duplicating_state(console_logs):
    """Test when the duplicated_item upload_state is not uploading, should abort the task."""

    item_to_duplicate = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    duplicated_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    console_logs.clear()
    duplicate_file(
        item_to_duplicate_id=item_to_duplicate.id,
        duplicated_item_id=duplicated_item.id,
    )

    assert console_logs == [
        {
            "event": (
                "duplicating file: the duplidated file upload_state is not duplicating but ready, "
                "aborting"
            ),
            "level": "error",
            "logger": "core.tasks.item",
        }
    ]


def test_duplicate_file():
    """Test duplicating file when all the condition are satisfied."""

    item_to_duplicate = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="my_file.txt",
    )
    duplicated_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.DUPLICATING,
        filename="my_file.txt",
    )

    default_storage.save(item_to_duplicate.file_key, BytesIO(b"my prose"))

    assert not default_storage.exists(duplicated_item.file_key)

    duplicate_file(
        item_to_duplicate_id=item_to_duplicate.id,
        duplicated_item_id=duplicated_item.id,
    )

    duplicated_item.refresh_from_db()

    assert duplicated_item.upload_state == models.ItemUploadStateChoices.READY
    assert default_storage.exists(duplicated_item.file_key)


def test_duplicate_file_retry(console_logs):
    """Test duplicating file should retry if a botocore exception is raised."""

    item_to_duplicate = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="my_file.txt",
    )
    duplicated_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.DUPLICATING,
        filename="my_file.txt",
    )
    # don't create a file to raise a botocore exception
    console_logs.clear()

    with pytest.raises(botocore.exceptions.ClientError):
        duplicate_file(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item.id,
        )

    assert console_logs == [
        {
            "event": (
                "duplicating file: error while copying file (retries 0 on 10). Error: An error "
                "occurred (NoSuchKey) when calling the CopyObject operation: The specified key "
                "does not exist."
            ),
            "level": "error",
            "logger": "core.tasks.item",
        }
    ]


def test_duplicate_file_max_retries_exceeded(console_logs):
    """Test duplicating file max retries exceeded should delete the duplicated item."""

    item_to_duplicate = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        filename="my_file.txt",
    )
    duplicated_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.DUPLICATING,
        filename="my_file.txt",
    )
    # don't create a file to raise a botocore exception
    console_logs.clear()

    with pytest.raises(botocore.exceptions.ClientError):
        duplicate_file.max_retries = 0
        duplicate_file(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item.id,
        )

    assert not models.Item.objects.filter(id=duplicated_item.id).exists()

    assert console_logs == [
        {
            "event": (
                f"duplicating file: 0 max retries exceeded, the duplicated item"
                f" {duplicated_item.id} is deleted"
            ),
            "level": "error",
            "logger": "core.tasks.item",
        },
        {
            "event": (
                "duplicating file: error while copying file (retries 0 on 0). Error: An error "
                "occurred (NoSuchKey) when calling the CopyObject operation: The specified key "
                "does not exist."
            ),
            "level": "error",
            "logger": "core.tasks.item",
        },
    ]
