"""Test the rename file task."""

from io import BytesIO

from django.core.files.storage import default_storage

import pytest

from core import factories, models
from core.tasks.item import rename_file

pytestmark = pytest.mark.django_db


def test_rename_file():
    """Test the rename file task."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        title="new_title",
        type=models.ItemTypeChoices.FILE,
        filename="old_title.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    default_storage.save(item.file_key, BytesIO(b"my prose"))

    rename_file(item.id, "new_title")
    item.refresh_from_db()
    assert item.filename == "new_title.txt"
    assert default_storage.exists(item.file_key)
    assert not default_storage.exists(f"{item.key_base}/old_title.txt")


def test_rename_file_origin_extension_is_kept():
    """The origin extension is kept no matter the new title."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        title="new_title.pdf",
        type=models.ItemTypeChoices.FILE,
        filename="old_title.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )
    default_storage.save(item.file_key, BytesIO(b"my prose"))

    rename_file(item.id, "new_title.pdf")
    item.refresh_from_db()
    assert item.filename == "new_title.pdf.txt"
    assert default_storage.exists(item.file_key)
    assert not default_storage.exists(f"{item.key_base}/old_title.txt")


def test_rename_file_filename_has_not_changed():
    """The filename has not changed, no need to move it on storage."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        title="new_title",
        type=models.ItemTypeChoices.FILE,
        filename="new_title.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )
    default_storage.save(item.file_key, BytesIO(b"my prose"))
    updated_at = item.updated_at
    file_key = item.file_key

    rename_file(item.id, "new_title")
    item.refresh_from_db()
    assert item.filename == "new_title.txt"
    assert item.updated_at == updated_at
    assert default_storage.exists(file_key)


def test_rename_file_item_not_ready(caplog):
    """Renaming a file that is not ready should abort the task."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        title="new_title",
        type=models.ItemTypeChoices.FILE,
        filename="old_title.txt",
        update_upload_state=models.ItemUploadStateChoices.PENDING,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )
    with caplog.at_level("ERROR", logger="core.tasks.item"):
        rename_file(item.id, "new_title")
    item.refresh_from_db()
    assert item.filename == "old_title.txt"
    assert f"Item {item.id} is not ready for renaming" in caplog.text


def test_rename_file_new_title_is_empty(caplog):
    """Renaming a file with an empty new title should abort the task."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        title="new_title",
        type=models.ItemTypeChoices.FILE,
        filename="old_title.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    with caplog.at_level("ERROR", logger="core.tasks.item"):
        rename_file(item.id, "")
    item.refresh_from_db()
    assert item.filename == "old_title.txt"
    assert "New title is empty, skipping rename file" in caplog.text


def test_rename_file_new_title_is_none(caplog):
    """Renaming a file with a None new title should abort the task."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        title="new_title",
        type=models.ItemTypeChoices.FILE,
        filename="old_title.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    with caplog.at_level("ERROR", logger="core.tasks.item"):
        rename_file(item.id, None)
    item.refresh_from_db()
    assert item.filename == "old_title.txt"
    assert "New title is empty, skipping rename file" in caplog.text
