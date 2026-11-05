"""Tests for the blob garbage-collection task."""

from datetime import timedelta
from io import BytesIO

from django.core.files.storage import default_storage
from django.utils import timezone

import pytest

from core import factories, models
from core.tasks.blob import gc_unreferenced_blob

pytestmark = pytest.mark.django_db


def test_gc_unreferenced_blob_past_grace_period():
    """A blob unreferenced since longer than the grace period is deleted, object included."""
    blob = factories.BlobFactory(
        unreferenced_at=timezone.now() - timedelta(hours=169, minutes=1)
    )
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
    blob = factories.BlobFactory(
        unreferenced_at=timezone.now() - timedelta(hours=169, minutes=1)
    )
    factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, filename="a.txt", blob=blob
    )
    default_storage.save(blob.file_key, BytesIO(b"shared"))

    gc_unreferenced_blob(blob.id)

    blob.refresh_from_db()
    assert blob.unreferenced_at is None
    assert default_storage.exists(blob.file_key)


def test_gc_unreferenced_blob_missing_object_still_drops_row():
    """A missing object is tolerated: the blob row is still deleted."""
    blob = factories.BlobFactory(
        unreferenced_at=timezone.now() - timedelta(hours=169, minutes=1)
    )

    gc_unreferenced_blob(blob.id)

    assert not models.Blob.objects.filter(id=blob.id).exists()


def test_gc_unreferenced_blob_does_not_exist():
    """An unknown blob id is a no-op."""
    gc_unreferenced_blob("00000000-0000-0000-0000-000000000000")
