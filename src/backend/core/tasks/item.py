"""
Tasks related to items.
"""

import hashlib
import logging
from datetime import timedelta
from os.path import splitext
from urllib.parse import quote

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from botocore.exceptions import ClientError
from celery.schedules import crontab

from core.models import Item, ItemTypeChoices, ItemUploadStateChoices
from core.utils.no_leak import safe_str_hash

from drive.celery_app import app

logger = logging.getLogger(__name__)

_CREATING_CLEANUP_MAX_ITEMS_PER_RUN = 200


@app.on_after_finalize.connect
def _setup_periodic_tasks(sender, **kwargs):
    """
    Periodic cleanup of stale "creating" OOXML placeholders (0-byte).

    The schedule is intentionally conservative to avoid load spikes.
    """
    sender.add_periodic_task(
        crontab(minute="*/5"),
        cleanup_stale_creating_items.s(),
        name="cleanup_stale_creating_items",
        serializer="json",
    )


@app.task
def cleanup_stale_creating_items():
    """
    Remove 0-byte items stuck in CREATING state past a TTL.

    Best-effort: items are soft+hard deleted then processed asynchronously to
    delete the object and the DB row.
    """
    ttl_seconds = int(getattr(settings, "ITEM_OOXML_CREATING_TTL_SECONDS", 900))
    ttl_seconds = max(ttl_seconds, 60)
    cutoff = timezone.now() - timedelta(seconds=ttl_seconds)

    stale = (
        Item.objects.filter(
            type=ItemTypeChoices.FILE,
            upload_state=ItemUploadStateChoices.CREATING,
            size=0,
            upload_started_at__isnull=False,
            upload_started_at__lt=cutoff,
            deleted_at__isnull=True,
            ancestors_deleted_at__isnull=True,
            hard_deleted_at__isnull=True,
        )
        .order_by("upload_started_at")
        .only("id", "filename", "upload_started_at", "deleted_at", "hard_deleted_at")
    )[:_CREATING_CLEANUP_MAX_ITEMS_PER_RUN]

    for item in stale:
        try:
            logger.info(
                "cleanup_stale_creating_items: hard-deleting stale creating item "
                "(item_id=%s file_key_hash=%s)",
                item.id,
                safe_str_hash(item.file_key) if item.filename else None,
            )
            item.soft_delete()
            item.hard_delete()
            process_item_deletion.delay(item.id)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception(
                "cleanup_stale_creating_items: failed to delete stale creating item "
                "(item_id=%s)",
                item.id,
            )


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
        logger.info("Deleting file (file_key_hash=%s)", safe_str_hash(item.file_key))
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

    escaped_key = quote(from_file_key, safe="/")
    copy_source = f"/{default_storage.bucket_name}/{escaped_key}"
    try:
        s3_client.copy_object(
            Bucket=default_storage.bucket_name,
            CopySource=copy_source,
            Key=to_file_key,
            MetadataDirective="COPY",
        )
    except ClientError:
        head = s3_client.head_object(
            Bucket=default_storage.bucket_name,
            Key=from_file_key,
        )
        obj = s3_client.get_object(
            Bucket=default_storage.bucket_name,
            Key=from_file_key,
        )
        s3_client.put_object(
            Bucket=default_storage.bucket_name,
            Key=to_file_key,
            Body=obj["Body"].read(),
            ContentType=head.get("ContentType"),
            Metadata=head.get("Metadata", {}),
            ACL="private",
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
