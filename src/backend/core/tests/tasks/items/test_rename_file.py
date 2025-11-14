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
