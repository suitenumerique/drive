"""Tasks related to blobs."""

import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

import botocore

from core.models import Blob, Item, ItemTypeChoices, ItemUploadStateChoices

from drive.celery_app import app

logger = logging.getLogger(__name__)


@app.task
def gc_unreferenced_blob(blob_id):
    """
    Delete a blob that lost its last reference beyond the grace period.

    The row is locked and re-checked inside a transaction so a concurrent
    re-attachment cannot lose content: if the blob got referenced again,
    unreferenced_at is cleared and nothing is deleted.
    """
    grace_cutoff = timezone.now() - timedelta(hours=settings.BLOB_UNREFERENCED_GRACE_HOURS)

    with transaction.atomic():
        try:
            blob = Blob.objects.select_for_update().get(pk=blob_id)
        except Blob.DoesNotExist:
            return

        if blob.unreferenced_at is None or blob.unreferenced_at > grace_cutoff:
            return

        if blob.items.exists() or blob.versions.exists():
            # Referenced again in the meantime: cancel the pending deletion.
            blob.unreferenced_at = None
            blob.save(update_fields=["unreferenced_at", "updated_at"])
            return

        try:
            default_storage.delete(blob.file_key)
        except FileNotFoundError:
            # Object already absent: still drop the row.
            pass

        blob.delete()
        logger.info("Garbage-collected unreferenced blob %s (%s)", blob.hash, blob_id)


@app.task(bind=True, max_retries=5)
def migrate_item_to_blob(self, item_id):
    """
    Migrate a legacy item (historical item/<uuid>/<filename> key) to a content-addressed
    blob: hash the stored object in streaming, copy it under blobs/<hash> conditionally
    on its ETag, then repoint the item under a lock after re-checking that the
    historical key still holds the hashed content. If the object changed in between,
    the migration aborts and the item is retried on the next run.
    """
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        return
    if (
        item.blob_id is not None
        or item.type != ItemTypeChoices.FILE
        or item.deleted_at
        or item.hard_deleted_at
    ):
        return

    s3_client = default_storage.connection.meta.client
    bucket = default_storage.bucket_name
    legacy_key = item.file_key

    try:
        head = s3_client.head_object(Bucket=bucket, Key=legacy_key)
    except botocore.exceptions.ClientError:
        logger.warning(
            "migrate_item_to_blob: object %s missing, skipping item %s", legacy_key, item_id
        )
        return
    etag = head["ETag"]

    # Hash the object in streaming, without holding it in memory.
    digest = hashlib.sha256()
    response = s3_client.get_object(Bucket=bucket, Key=legacy_key)
    for chunk in response["Body"].iter_chunks(8 * 1024 * 1024):
        digest.update(chunk)
    blob_hash = digest.hexdigest()

    # Copy under the content-addressed key, tied to the ETag read above: if the
    # historical object was rewritten in between, the copy fails and we retry later.
    try:
        s3_client.copy_object(
            Bucket=bucket,
            Key=f"blobs/{blob_hash}",
            CopySource={"Bucket": bucket, "Key": legacy_key},
            CopySourceIfMatch=etag,
            MetadataDirective="COPY",
        )
    except botocore.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] in ("PreconditionFailed", "412"):
            logger.info(
                "migrate_item_to_blob: %s changed during migration of item %s, retrying later",
                legacy_key,
                item_id,
            )
            self.retry(exc=exc)
        raise

    with transaction.atomic():
        locked_item = Item.objects.select_for_update().get(pk=item_id)
        if locked_item.blob_id is not None or locked_item.deleted_at or locked_item.hard_deleted_at:
            return

        # Re-check the historical key still holds the hashed content before repointing.
        try:
            head_after = s3_client.head_object(Bucket=bucket, Key=legacy_key)
        except botocore.exceptions.ClientError as exc:
            self.retry(exc=exc)
            return
        if head_after.get("ETag") != etag:
            logger.info(
                "migrate_item_to_blob: %s changed during migration of item %s, aborting",
                legacy_key,
                item_id,
            )
            return

        blob, _created = Blob.objects.get_or_create(
            hash=blob_hash,
            defaults={
                "size": head["ContentLength"],
                "upload_state": (
                    ItemUploadStateChoices.SUSPICIOUS
                    if locked_item.upload_state == ItemUploadStateChoices.SUSPICIOUS
                    else ItemUploadStateChoices.READY
                ),
            },
        )
        locked_item.blob = blob
        locked_item.save(update_fields=["blob", "updated_at"])
        logger.info("Migrated item %s to blob %s", item_id, blob_hash)
