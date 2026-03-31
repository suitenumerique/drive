"""
Tasks related to items.
"""

import hashlib
import logging
from os.path import splitext

from django.core.files.storage import default_storage

import boto3
import botocore

from core.api.utils import sanitize_filename
from core.models import Item, ItemTypeChoices, ItemUploadStateChoices
from core.tasks.storage import duplicate_file_on_mirroring_bucket, rename_file_on_mirroring_bucket

from drive.celery_app import app

logger = logging.getLogger(__name__)


@app.task
def process_item_deletion(item_id):
    """
    Process the deletion of an item.
    Definitely delete it in the database.
    Delete the files from the storage.
    trigger the deletion process of the children.
    """
    logger.info("Processing item deletion for %s", item_id)
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("Item %s does not exist", item_id)
        return

    if item.hard_deleted_at is None:
        logger.error("To process an item deletion, it must be hard deleted first.")
        return

    if item.type == ItemTypeChoices.FILE:
        logger.info("Deleting file %s", item.file_key)
        default_storage.delete(item.file_key)

    if item.type == ItemTypeChoices.FOLDER:
        for child in item.children():
            process_item_deletion.delay(child.id)

    item.delete()


@app.task
def rename_file(item_id, new_title):
    """Rename the file of an item. Update the filename and then rename the file on storage."""

    if not new_title:
        logger.error("New title is empty, skipping rename file")
        return

    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("Item %s does not exist", item_id)
        return

    if item.type != ItemTypeChoices.FILE:
        logger.error("Item %s is not a file", item_id)
        return

    if item.upload_state != ItemUploadStateChoices.READY:
        logger.error("Item %s is not ready for renaming", item_id)
        return

    _, extension = splitext(item.filename)

    new_filename = sanitize_filename(f"{new_title}{extension}")
    from_file_key = item.file_key

    if item.filename == new_filename:
        logger.info(
            "Item %s filename has not changed, no need to move it on storage",
            item_id,
        )
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

    rename_file_on_mirroring_bucket.delay(item.id, from_file_key, to_file_key)


@app.task
def update_suspicious_item_file_hash(item_id):
    """
    Update the file hash of a suspicious item.
    This is done in a separate task to avoid blocking the main thread.
    """
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("updating suspicious item file hash: Item %s does not exist", item_id)
        return
    if item.upload_state != ItemUploadStateChoices.SUSPICIOUS:
        logger.error("updating suspicious item file hash: Item %s is not suspicious", item_id)
        return
    with default_storage.open(item.file_key, "rb") as file:
        file_hash = hashlib.file_digest(file, "sha256").hexdigest()

    item.malware_detection_info.update({"file_hash": file_hash})
    item.save(update_fields=["malware_detection_info"])


@app.task(bind=True, max_retries=10)
def duplicate_file(self, item_to_duplicate_id, duplicated_item_id):
    """Duplicate a file on the storage by creating a copy of the original file."""
    try:
        item_to_duplicate = Item.objects.get(id=item_to_duplicate_id)
    except Item.DoesNotExist:
        logger.exception(
            "duplicating file: item_to_duplicate with id %s does not exist, aborting",
            item_to_duplicate_id,
        )
        return

    try:
        duplicated_item = Item.objects.get(id=duplicated_item_id)
    except Item.DoesNotExist:
        logger.exception(
            "duplicating file: duplicated_item with id %s does not exist, aborting",
            duplicated_item_id,
        )
        return

    if duplicated_item.upload_state != ItemUploadStateChoices.DUPLICATING:
        logger.error(
            "duplicating file: the duplidated file upload_state is not duplicating but %s, "
            "aborting",
            duplicated_item.upload_state,
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
                "duplicating file: %d max retries exceeded, the duplicated item %s is deleted",
                self.max_retries,
                duplicated_item.id,
            )
            duplicated_item.soft_delete()
            duplicated_item.delete()

        logger.error(
            "duplicating file: error while copying file (retries %d on %d). Error: %s",
            self.request.retries,
            self.max_retries,
            exc,
        )

        self.retry(exc=exc)

    duplicated_item.upload_state = ItemUploadStateChoices.READY
    duplicated_item.save(update_fields=["upload_state", "updated_at"])

    duplicate_file_on_mirroring_bucket.delay(
        duplicated_item.id, item_to_duplicate.file_key, duplicated_item.file_key
    )
