"""Tests for the blob garbage-collection and legacy migration tasks."""

import hashlib
import secrets
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

import pytest

from core import factories, models
from core.tasks.blob import gc_unreferenced_blob, migrate_item_to_blob

# pylint: disable=no-value-for-parameter

pytestmark = pytest.mark.django_db


def test_gc_unreferenced_blob_past_grace_period():
    """A blob unreferenced since longer than the grace period is deleted, object included."""
    blob = factories.BlobFactory(unreferenced_at=timezone.now() - timedelta(hours=169, minutes=1))
    default_storage.save(blob.file_key, BytesIO(b"orphan"))

    gc_unreferenced_blob(blob.id)

    assert not models.Blob.objects.filter(id=blob.id).exists()
    assert not default_storage.exists(blob.file_key)


def test_gc_unreferenced_blob_within_grace_period_is_kept():
    """A blob unreferenced more recently than the grace period is kept."""
    blob = factories.BlobFactory(unreferenced_at=timezone.now() - timedelta(hours=1))
    default_storage.save(blob.file_key, BytesIO(b"recent"))

    gc_unreferenced_blob(blob.id)

    blob.refresh_from_db()
    assert blob.unreferenced_at is not None
    assert default_storage.exists(blob.file_key)


def test_gc_unreferenced_blob_still_referenced_is_kept():
    """A blob that got referenced again before collection keeps its content and is
    marked referenced again."""
    blob = factories.BlobFactory(unreferenced_at=timezone.now() - timedelta(hours=169, minutes=1))
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, filename="a.txt", blob=blob)
    default_storage.save(blob.file_key, BytesIO(b"shared"))

    gc_unreferenced_blob(blob.id)

    blob.refresh_from_db()
    assert blob.unreferenced_at is None
    assert default_storage.exists(blob.file_key)


def test_gc_unreferenced_blob_missing_object_still_drops_row():
    """A missing object is tolerated: the blob row is still deleted."""
    blob = factories.BlobFactory(unreferenced_at=timezone.now() - timedelta(hours=169, minutes=1))

    gc_unreferenced_blob(blob.id)

    assert not models.Blob.objects.filter(id=blob.id).exists()


def test_gc_unreferenced_blob_does_not_exist():
    """An unknown blob id is a no-op."""
    gc_unreferenced_blob("00000000-0000-0000-0000-000000000000")


def test_migrate_item_to_blob_success():
    """A legacy item is repointed to a blob copied under blobs/<sha256>; the historical
    object is kept and file_key now resolves to the blob key."""
    # unique content: identical contents share the same blob key across xdist workers
    content = b"legacy content " + secrets.token_bytes(8)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="legacy.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    default_storage.save(item.file_key, BytesIO(content))

    migrate_item_to_blob(item.id)

    item.refresh_from_db()
    expected_hash = hashlib.sha256(content).hexdigest()
    assert item.blob is not None
    assert item.blob.hash == expected_hash
    assert item.blob.size == len(content)
    assert item.blob.upload_state == models.ItemUploadStateChoices.READY
    assert default_storage.exists(f"blobs/{expected_hash}")
    # the historical object is kept during the migration
    assert default_storage.exists(item.public_file_key)
    # double reading: file_key now resolves to the blob key
    assert item.file_key == f"blobs/{expected_hash}"


def test_migrate_item_to_blob_already_migrated_is_noop():
    """An item already attached to a blob is left alone."""
    # random hash: the factory sequence collides across xdist workers
    blob = factories.BlobFactory(hash=secrets.token_hex(32))
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="legacy.txt",
        blob=blob,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    migrate_item_to_blob(item.id)

    item.refresh_from_db()
    assert item.blob_id == blob.id
    assert not default_storage.exists(f"blobs/{blob.hash}")


def test_migrate_item_to_blob_missing_object_skips():
    """An item whose object is absent from storage is skipped, not repointed."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="ghost.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    migrate_item_to_blob(item.id)

    item.refresh_from_db()
    assert item.blob_id is None


def test_migrate_item_to_blob_aborts_when_legacy_object_changed(monkeypatch):
    """If the historical object changed between the two head checks, the item is not
    repointed (the copy was tied to the first ETag)."""
    content = b"legacy content"
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="legacy.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    default_storage.save(item.file_key, BytesIO(content))

    client = default_storage.connection.meta.client
    etags = iter(['"first"', '"second"'])
    monkeypatch.setattr(
        client, "head_object", lambda **kwargs: {"ETag": next(etags), "ContentLength": len(content)}
    )
    monkeypatch.setattr(client, "copy_object", lambda **kwargs: {})

    migrate_item_to_blob(item.id)

    item.refresh_from_db()
    assert item.blob_id is None


def test_migrate_items_to_blobs_command_filters_eligible_items():
    """The command queues only READY, non-deleted files that have no blob yet."""
    factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="a.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="b.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    # not eligible: already migrated / pending / deleted / folder
    factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="c.txt",
        blob=factories.BlobFactory(),
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="d.txt",
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, filename=None)

    with mock.patch(
        "core.management.commands.migrate_items_to_blobs.migrate_item_to_blob"
    ) as mock_task:
        call_command("migrate_items_to_blobs")

    assert mock_task.delay.call_count == 2
