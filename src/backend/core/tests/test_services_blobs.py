"""Tests for the blob service helpers."""

import hashlib

from django.core.files.storage import default_storage

import pytest

from core.models import ItemUploadStateChoices
from core.services.blobs import store_content_as_blob

pytestmark = pytest.mark.django_db


def test_store_content_as_blob_creates_blob_and_object():
    """The content is written under blobs/<sha256> and a READY blob is returned."""
    content = b"hello blob"
    blob = store_content_as_blob(content)

    assert blob.hash == hashlib.sha256(content).hexdigest()
    assert blob.size == len(content)
    assert blob.upload_state == ItemUploadStateChoices.READY
    assert default_storage.exists(blob.file_key)
    with default_storage.open(blob.file_key, "rb") as fd:
        assert fd.read() == content


def test_store_content_as_blob_is_idempotent_and_keeps_state():
    """Storing the same content twice reuses the blob and keeps its analysis state."""
    content = b"hello blob"
    first = store_content_as_blob(content)
    first.upload_state = ItemUploadStateChoices.ANALYZING
    first.save(update_fields=["upload_state", "updated_at"])

    second = store_content_as_blob(content)

    assert second.pk == first.pk
    second.refresh_from_db()
    assert second.upload_state == ItemUploadStateChoices.ANALYZING
