"""Service for exporting item folders as streaming ZIP archives."""

import logging

from django.core.files.storage import default_storage

from zipstream import ZipStream

from core import models

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_READ_CHUNK_SIZE = 64 * 1024


def iter_storage_chunks(file_key, chunk_size=DEFAULT_STORAGE_READ_CHUNK_SIZE):
    """Yield bytes from object storage without buffering the whole file."""
    # default_storage.open() would download the whole object in memory before
    # the first read, so stream straight from the boto3 response body instead.
    s3_client = default_storage.connection.meta.client
    bucket_name = default_storage.bucket_name
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    except s3_client.exceptions.NoSuchKey:
        # A database row references an object that is gone from storage:
        # aborting would make the folder export fail forever, so keep the
        # archive going with an empty entry for this file.
        logger.warning("Export: object %s is missing from storage, skipped", file_key)
        return
    yield from response["Body"].iter_chunks(chunk_size)


def export_descendants(folder):
    """
    Yield (file_key_or_None, archive_path) tuples for a folder's subtree.

    Walks descendants ordered by path, skips descendants whose ancestors are
    soft-deleted, computes the relative archive path for each item, and emits
    a directory entry (`file_key=None`, trailing slash) for folders or a file
    entry for `FILE` items in the `READY` upload state.
    """
    descendants = folder.descendants().filter(ancestors_deleted_at__isnull=True).order_by("path")

    relative_paths = {str(folder.path): ""}
    for descendant in descendants:
        # Shortcuts are tree entries: their target lives in another subtree
        if descendant.type == models.ItemTypeChoices.SHORTCUT:
            continue

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

        if descendant.type == models.ItemTypeChoices.FOLDER:
            yield None, f"{relative}/"
        elif descendant.upload_state == models.ItemUploadStateChoices.READY:
            yield descendant.file_key, relative


def build_zip_stream(descendants):
    """Build a ZIP stream that lazily reads exported files from storage."""
    zip_stream = ZipStream(sized=False)
    for file_key, archive_path in descendants:
        if file_key is None:
            zip_stream.mkdir(archive_path)
        else:
            zip_stream.add(
                data=iter_storage_chunks(file_key),
                arcname=archive_path,
            )
    return zip_stream
