"""
Tasks related to items.
"""

import hashlib
import logging
from os.path import splitext

from django.core.files.storage import default_storage

from core.models import Item, ItemTypeChoices, ItemUploadStateChoices

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

    if (
        item.type == ItemTypeChoices.FILE
        and item.upload_state == ItemUploadStateChoices.READY
    ):
        logger.info("Deleting file %s", item.file_key)
        default_storage.delete(item.file_key)

    if item.type == ItemTypeChoices.FOLDER:
        for child in item.children():
            process_item_deletion.delay(child.id)

    item.delete()


@app.task
def rename_file(item_id, new_title):
    """Rename the file of an item. Update the filename and then rename the file on storage."""
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

    new_filename = f"{new_title}{extension}"
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


@app.task
def update_suspicious_item_file_hash(item_id):
    """
    Update the file hash of a suspicious item.
    This is done in a separate task to avoid blocking the main thread.
    """
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error(
            "updating suspicious item file hash: Item %s does not exist", item_id
        )
        return
    if item.upload_state != ItemUploadStateChoices.SUSPICIOUS:
        logger.error(
            "updating suspicious item file hash: Item %s is not suspicious", item_id
        )
        return
    with default_storage.open(item.file_key, "rb") as file:
        file_hash = hashlib.file_digest(file, "sha256").hexdigest()

    item.malware_detection_info.update({"file_hash": file_hash})
    item.save(update_fields=["malware_detection_info"])
