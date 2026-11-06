"""Tests for the item versioning services."""

from unittest import mock

from django.core.files.storage import default_storage

import pytest

from core import factories, models
from core.services.item_versions import (
    delete_version,
    next_version_number,
    restore_version,
    snapshot_version,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def s3_client():
    """Stub object storage so versioning tests do not need a live bucket."""
    with (
        mock.patch(
            "core.services.item_versions.default_storage.exists",
            return_value=True,
        ),
        mock.patch("core.services.item_versions._s3") as s3,
    ):
        yield s3


def _make_file_item(**kwargs):
    defaults = {
        "type": models.ItemTypeChoices.FILE,
        "update_upload_state": models.ItemUploadStateChoices.READY,
        "filename": "content.txt",
        "mimetype": "text/plain",
        "size": 5,
    }
    defaults.update(kwargs)
    return factories.ItemFactory(**defaults)


def test_snapshot_version_ignores_non_file_items():
    """Folders and unknown items must not be versioned."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    assert snapshot_version(folder) is None
    assert not models.ItemVersion.objects.exists()


def test_snapshot_version_ignores_pending_files():
    """Files whose content is not final yet must not be versioned."""
    item = _make_file_item(update_upload_state=models.ItemUploadStateChoices.PENDING)
    assert snapshot_version(item) is None
    assert not models.ItemVersion.objects.exists()


def test_snapshot_version_copies_current_bytes(s3_client):
    """Snapshotting stores the current content of the file as a version."""
    item = _make_file_item()

    version = snapshot_version(item, created_by=item.creator)

    assert version.version_number == 1
    assert version.filename == item.filename
    assert version.mimetype == item.mimetype
    assert version.size == item.size
    assert version.created_by == item.creator
    s3_client.return_value.copy_object.assert_called_once_with(
        Bucket=default_storage.bucket_name,
        Key=version.file_key,
        CopySource={"Bucket": default_storage.bucket_name, "Key": item.file_key},
    )


@pytest.mark.usefixtures("s3_client")
def test_snapshot_version_increments_number():
    """Each snapshot on the same item uses an incremented version number."""
    item = _make_file_item()
    snapshot_version(item)
    second = snapshot_version(item)
    assert second.version_number == 2


def test_next_version_number_starts_at_one():
    """The first version number is 1 when no version exists yet."""
    item = _make_file_item()
    assert next_version_number(item) == 1


@pytest.mark.usefixtures("s3_client")
def test_enforce_max_versions_keeps_only_latest():
    """Only the configured maximum number of versions is kept."""
    item = _make_file_item()

    created = []
    for _ in range(7):
        created.append(snapshot_version(item))

    assert all(version is not None for version in created)
    remaining = list(item.versions.order_by("version_number"))
    assert len(remaining) == 5
    assert [v.version_number for v in remaining] == [3, 4, 5, 6, 7]
    deleted = models.ItemVersion.objects.filter(version_number__in=[1, 2])
    assert not deleted.exists()


def test_restore_snapshots_current_and_updates_item(s3_client):
    """Restoring keeps the current content as a new version and promotes the target."""
    item = _make_file_item()

    old = snapshot_version(item)  # version 1 (older content)
    item.size = 10
    item.mimetype = "text/html"
    item.save(update_fields=["size", "mimetype"])

    s3_client.reset_mock()
    restore_version(old, created_by=item.creator)

    item.refresh_from_db()
    # Content is restored: size and mimetype come back from the version.
    assert item.size == 5
    assert item.mimetype == "text/plain"
    # The filename is kept as-is to avoid sibling collisions.
    assert item.filename == "content.txt"
    # A snapshot of the pre-restore content was created (version 2).
    assert item.versions.filter(version_number=2).exists()
    # The restored version is now the live file and its record is removed.
    assert not models.ItemVersion.objects.filter(pk=old.pk).exists()


def test_delete_version_removes_storage_and_record(s3_client):
    """Deleting a version removes its storage bytes and its record."""
    item = _make_file_item()
    version = snapshot_version(item)
    s3_client.reset_mock()

    delete_version(version)

    s3_client.return_value.delete_object.assert_called_once_with(
        Bucket=default_storage.bucket_name, Key=version.file_key
    )
    assert not models.ItemVersion.objects.filter(pk=version.pk).exists()


def test_max_versions_cap_is_five_by_default(settings):
    """The default configured cap is 5."""
    assert settings.MAX_ITEM_VERSIONS == 5
