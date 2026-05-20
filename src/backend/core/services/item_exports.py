"""Service for exporting item folders as streaming ZIP archives."""

from django.core.files.storage import default_storage

from zipstream import ZipStream

from core import models

DEFAULT_STORAGE_READ_CHUNK_SIZE = 1024


def iter_storage_chunks(file_key, chunk_size=DEFAULT_STORAGE_READ_CHUNK_SIZE):
    """Yield bytes from object storage without buffering the whole file."""
    with default_storage.open(file_key, "rb") as fh:
        while chunk := fh.read(chunk_size):
            yield chunk


def export_descendants(folder):
    """
    Yield (file_key, archive_path) tuples for the READY files of a folder's subtree.

    Walks descendants ordered by path, skips descendants whose ancestors are
    soft-deleted, computes the relative archive path for each item, and emits
    a tuple only for `FILE` items in the `READY` upload state.
    """
    descendants = folder.descendants().filter(ancestors_deleted_at__isnull=True).order_by("path")

    relative_paths = {str(folder.path): ""}
    for descendant in descendants:
        parent_key = str(descendant.path).rsplit(".", 1)[0]
        parent_relative = relative_paths.get(parent_key)
        if parent_relative is None:
            continue

        name = (
            descendant.filename
            if descendant.type == models.ItemTypeChoices.FILE
            else descendant.title
        )
        relative = f"{parent_relative}/{name}" if parent_relative else name
        relative_paths[str(descendant.path)] = relative

        if (
            descendant.type == models.ItemTypeChoices.FILE
            and descendant.upload_state == models.ItemUploadStateChoices.READY
        ):
            yield descendant.file_key, relative


def build_zip_stream(descendants):
    """Build a ZIP stream that lazily reads exported files from storage."""
    zip_stream = ZipStream(sized=False)
    for file_key, archive_path in descendants:
        zip_stream.add(
            data=iter_storage_chunks(file_key),
            arcname=archive_path,
        )
    return zip_stream
