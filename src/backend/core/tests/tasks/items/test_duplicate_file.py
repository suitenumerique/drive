"""Module for the tests related to the duplicate_file celery task."""

import uuid
from io import BytesIO

from django.core.files.storage import default_storage

import botocore
import pytest

from core import factories, models
from core.tasks.item import duplicate_file

pytestmark = pytest.mark.django_db

# As the task is bound, we need to ignore this error.
# pylint: disable=no-value-for-parameter


def test_duplicate_file_item_to_duplicate_does_not_exist(caplog):
    """Test when the item_to_duplicate does not exists, should abort the task."""

    with caplog.at_level("ERROR", logger="core.tasks.item"):
        item_to_duplicate_id = uuid.uuid4()
        duplicate_file(item_to_duplicate_id=item_to_duplicate_id, duplicated_item_id=uuid.uuid4())

    assert (
        f"duplicating file: item_to_duplicate with id {item_to_duplicate_id} does not exist, "
        "aborting" in caplog.text
    )


def test_duplicate_file_duplicated_item_does_not_exist(caplog):
    """Test when the duplicated_item does not exists, should abort the task."""

    item_to_duplicate = factories.ItemFactory(type=models.ItemTypeChoices.FILE)

    with caplog.at_level("ERROR", logger="core.tasks.item"):
        duplicated_item_id = uuid.uuid4()
        duplicate_file(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item_id,
        )

    assert (
        f"duplicating file: duplicated_item with id {duplicated_item_id} does not exist, aborting"
        in caplog.text
    )


def test_duplicate_file_duplicated_file_not_in_duplicating_state(caplog):
    """Test when the duplicated_item upload_state is not uploading, should abort the task."""

    item_to_duplicate = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    duplicated_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    with caplog.at_level("ERROR", logger="core.tasks.item"):
        duplicate_file(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item.id,
        )

    assert (
        "duplicating file: the duplidated file upload_state is not duplicating but ready, "
        "aborting" in caplog.text
    )


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


def test_duplicate_file_retry(caplog):
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

    with (
        caplog.at_level("ERROR", logger="core.tasks.item"),
        pytest.raises(botocore.exceptions.ClientError),
    ):
        duplicate_file(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item.id,
        )

    assert (
        "duplicating file: error while copying file (retries 0 on 10). Error: An error occurred "
        "(NoSuchKey) when calling the CopyObject operation: The specified key does not exist."
        in caplog.text
    )


def test_duplicate_file_max_retries_exceeded(caplog):
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

    with (
        caplog.at_level("ERROR", logger="core.tasks.item"),
        pytest.raises(botocore.exceptions.ClientError),
    ):
        duplicate_file.max_retries = 0
        duplicate_file(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item.id,
        )

    assert not models.Item.objects.filter(id=duplicated_item.id).exists()

    assert (
        f"duplicating file: 0 max retries exceeded, the duplicated item {duplicated_item.id} is"
        " deleted" in caplog.text
    )
