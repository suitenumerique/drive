"""Tests for the item_exports service."""

import uuid
from io import BytesIO

from django.core.files.storage import default_storage

import pytest

from core import factories, models
from core.services.item_exports import export_descendants, iter_storage_chunks

pytestmark = pytest.mark.django_db


@pytest.fixture(name="stored_blob")
def fixture_stored_blob():
    """Save a blob in object storage and yield its key, cleaning up after."""
    key = f"test/iter_storage_chunks-{uuid.uuid4()}.bin"
    payload = b"abcdefghij" * 10
    default_storage.save(key, BytesIO(payload))
    try:
        yield key, payload
    finally:
        default_storage.delete(key)


def test_services_item_exports_iter_storage_chunks_returns_full_content(stored_blob):
    """Concatenated chunks rebuild the original payload."""
    key, payload = stored_blob

    assert b"".join(iter_storage_chunks(key)) == payload


def test_services_item_exports_iter_storage_chunks_respects_chunk_size(stored_blob):
    """A small chunk_size yields several chunks bounded by that size."""
    key, payload = stored_blob

    chunks = list(iter_storage_chunks(key, chunk_size=8))

    assert len(chunks) > 1
    assert all(len(chunk) <= 8 for chunk in chunks)
    assert b"".join(chunks) == payload


def test_services_item_exports_iter_storage_chunks_empty_file():
    """An empty stored file yields no chunks."""
    key = f"test/iter_storage_chunks-empty-{uuid.uuid4()}.bin"
    default_storage.save(key, BytesIO(b""))

    try:
        chunks = list(iter_storage_chunks(key))
        assert not chunks
    finally:
        default_storage.delete(key)


def test_services_item_exports_export_descendants_yields_file_key_and_relative_archive_path():
    """A single ready file is emitted as one (file_key, archive_path) tuple."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    file_item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="hello.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    descendants = list(export_descendants(folder))

    assert descendants == [(file_item.file_key, "hello.txt")]


def test_services_item_exports_export_descendants_builds_hierarchical_archive_path():
    """Files nested in subfolders carry their folder path in archive_path."""
    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    sub = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER, title="sub")
    top_file = factories.ItemFactory(
        parent=root,
        type=models.ItemTypeChoices.FILE,
        filename="top.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    nested_file = factories.ItemFactory(
        parent=sub,
        type=models.ItemTypeChoices.FILE,
        filename="nested.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    by_archive_path = {
        archive_path: file_key for file_key, archive_path in export_descendants(root)
    }

    assert by_archive_path == {
        "top.txt": top_file.file_key,
        "sub/nested.txt": nested_file.file_key,
    }


@pytest.mark.parametrize(
    "upload_state",
    [
        models.ItemUploadStateChoices.PENDING,
        models.ItemUploadStateChoices.DUPLICATING,
    ],
)
def test_services_item_exports_export_descendants_skips_non_ready_files(upload_state):
    """Only files in the READY upload state are yielded."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="busy.txt",
        upload_state=upload_state,
    )
    ready = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="ready.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    descendants = list(export_descendants(folder))

    assert [file_key for file_key, _ in descendants] == [ready.file_key]


def test_services_item_exports_export_descendants_skips_soft_deleted_descendants():
    """Descendants under a soft-deleted ancestor are excluded."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="keep.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    deleted_sub = factories.ItemFactory(parent=folder, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(
        parent=deleted_sub,
        type=models.ItemTypeChoices.FILE,
        filename="drop.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    deleted_sub.soft_delete()

    descendants = list(export_descendants(folder))

    assert [archive_path for _, archive_path in descendants] == ["keep.txt"]
