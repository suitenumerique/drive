"""
Tasks related to items.
"""

import hashlib
from datetime import timedelta
from os.path import splitext

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

import boto3
import botocore
import structlog
from lasuite.malware_detection.models import MalwareDetection

from core.api.utils import sanitize_filename
from core.models import Item, ItemTypeChoices, ItemUploadStateChoices

from drive.celery_app import app

logger = structlog.get_logger(__name__)


@app.task
def process_item_purge(item_id):
    """
    Process the purge of an item that was either:
    - hard deleted
    - soft deleted for longer than the trashbin grace period

    This task can be retried without harm:
    - delete file from storage first, then item from database
    - delete children first, then parents
    """
    logger.info("item_purge_started", item_id=item_id)

    try:
        root = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("item_purge_item_not_found", item_id=item_id)
        return

    # Compute cutoff only if relevant
    now = timezone.now()

    is_hard_deleted = root.hard_deleted_at is not None
    is_soft_deleted_and_purgeable = root.deleted_at is not None and now >= (
        root.deleted_at + timedelta(days=settings.TRASHBIN_CUTOFF_DAYS + settings.PURGE_GRACE_DAYS)
    )

    if not (is_hard_deleted or is_soft_deleted_and_purgeable):
        logger.info(
            "item_purge_skipped",
            item_id=item_id,
            reason="not_deleted" if root.deleted_at is None else "not_past_purge_cutoff",
            deleted_at=root.deleted_at,
        )
        return

    # Get descendants, leaf first. Don't burst memory
    for item in Item.objects.filter(path__descendants=root.path).order_by("-path").iterator():
        if item.type == ItemTypeChoices.FILE and item.file_key:
            try:
                default_storage.delete(item.file_key)
            except FileNotFoundError:
                # File already absent from storage: ignore and continue
                pass

            # Drop any malware detection record so the analysis is not relaunched
            MalwareDetection.objects.filter(path=item.file_key).delete()

        item.delete()


@app.task
def rename_file(item_id, new_title):
    """Rename the file of an item. Update the filename and then rename the file on storage."""

    if not new_title:
        logger.error("file_rename_empty_title", item_id=item_id)
        return

    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("file_rename_item_not_found", item_id=item_id)
        return

    if item.type != ItemTypeChoices.FILE:
        logger.error("file_rename_item_not_a_file", item_id=item_id)
        return

    if item.upload_state != ItemUploadStateChoices.READY:
        logger.error("file_rename_item_not_ready", item_id=item_id, upload_state=item.upload_state)
        return

    _, extension = splitext(item.filename)

    new_filename = sanitize_filename(f"{new_title}{extension}")
    from_file_key = item.file_key

    if item.filename == new_filename:
        logger.info("file_rename_unchanged", item_id=item_id)
        return

    item.filename = new_filename
    item.save(update_fields=["filename", "updated_at"])

    to_file_key = item.file_key

    s3_client = default_storage.connection.meta.client

    s3_client.copy_object(
        Bucket=default_storage.bucket_name,
        CopySource={
            "Bucket": default_storage.bucket_name,
            "Key": from_file_key,
        },
        Key=to_file_key,
        MetadataDirective="COPY",
    )

    s3_client.delete_object(
        Bucket=default_storage.bucket_name,
        Key=from_file_key,
    )


@app.task
def update_suspicious_item_file_hash(item_id):
    """
    Update the file hash of a suspicious item.
    This is done in a separate task to avoid blocking the main thread.
    """
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("suspicious_file_hash_item_not_found", item_id=item_id)
        return
    if item.upload_state != ItemUploadStateChoices.SUSPICIOUS:
        logger.error(
            "suspicious_file_hash_item_not_suspicious",
            item_id=item_id,
            upload_state=item.upload_state,
        )
        return
    with default_storage.open(item.file_key, "rb") as file:
        file_hash = hashlib.file_digest(file, "sha256").hexdigest()

    item.malware_detection_info.update({"file_hash": file_hash})
    item.save(update_fields=["malware_detection_info"])


@app.task(bind=True, max_retries=10)
def duplicate_file(self, item_to_duplicate_id, duplicated_item_id):
    """Copy a file on the storage."""
    try:
        item_to_duplicate = Item.objects.get(id=item_to_duplicate_id)
    except Item.DoesNotExist:
        logger.exception("file_duplication_source_not_found", item_id=item_to_duplicate_id)
        return

    try:
        duplicated_item = Item.objects.get(id=duplicated_item_id)
    except Item.DoesNotExist:
        logger.exception("file_duplication_copy_not_found", item_id=duplicated_item_id)
        return

    if duplicated_item.upload_state != ItemUploadStateChoices.DUPLICATING:
        logger.error(
            "file_duplication_copy_not_duplicating",
            item_id=duplicated_item_id,
            upload_state=duplicated_item.upload_state,
        )
        return

    s3_client = default_storage.connection.meta.client

    try:
        s3_client.copy_object(
            Bucket=default_storage.bucket_name,
            CopySource={
                "Bucket": default_storage.bucket_name,
                "Key": item_to_duplicate.file_key,
            },
            Key=duplicated_item.file_key,
            MetadataDirective="COPY",
        )
    except (
        boto3.exceptions.Boto3Error,
        botocore.exceptions.BotoCoreError,
        botocore.exceptions.ClientError,
    ) as exc:
        if self.request.retries >= self.max_retries:
            # delete the duplicated item
            logger.error(
                "file_duplication_abandoned",
                item_id=duplicated_item_id,
                max_retries=self.max_retries,
            )
            duplicated_item.soft_delete()
            duplicated_item.delete()

        logger.error(
            "file_duplication_failed",
            item_id=duplicated_item_id,
            retries=self.request.retries,
            max_retries=self.max_retries,
            error=str(exc),
        )

        self.retry(exc=exc)

    duplicated_item.upload_state = ItemUploadStateChoices.READY
    duplicated_item.save(update_fields=["upload_state", "updated_at"])
