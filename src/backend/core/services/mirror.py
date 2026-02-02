"""Services related to mirroring."""

import logging
from uuid import UUID

from core.models import Item, MirrorItemTask, MirrorItemTaskStatusChoices
from core.tasks.storage import get_mirror_s3_client, mirror_file

logger = logging.getLogger(__name__)


def mirror_item_from_file_key(file_key: str):
    """Mirror an item from a file key."""

    if not file_key.startswith("item/"):
        logger.error("File key %s is not a valid item file key", file_key)
        return

    # key is in the form item/<item_id>/<filename>
    parts = file_key.split("/")

    try:
        item_id = UUID(parts[1])
    except ValueError:
        logger.error("Item ID %s is not a valid UUID", parts[1])
        return

    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        logger.error("Item %s does not exist", item_id)
        return
    mirror_item(item)


def mirror_item(item: Item):
    """Mirror an item to the mirroring S3 bucket."""
    mirror_s3_client = get_mirror_s3_client()
    if not mirror_s3_client:
        logger.info("Mirroring S3 bucket is not configured, skipping mirroring")
        return

    mirror_task = MirrorItemTask.objects.create(
        item=item, status=MirrorItemTaskStatusChoices.PENDING
    )

    mirror_file.delay(mirror_task.id)
