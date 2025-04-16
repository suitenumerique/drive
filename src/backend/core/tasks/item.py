"""
Tasks related to items.
"""

import logging

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
        and item.upload_state == ItemUploadStateChoices.UPLOADED
    ):
        logger.info("Deleting file %s", item.file_key)
        default_storage.delete(item.file_key)

    if item.type == ItemTypeChoices.FOLDER:
        for child in item.children():
            process_item_deletion.delay(child.id)

    item.delete()
