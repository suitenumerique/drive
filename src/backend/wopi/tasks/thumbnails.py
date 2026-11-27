"""Celery tasks for WOPI document thumbnails."""

import logging

from django.core.cache import cache

from core import models
from wopi.conversion.exceptions import ConversionProviderError
from wopi.conversion.thumbnails import generate_thumbnail

from drive.celery_app import app

logger = logging.getLogger(__name__)

# Seconds the pending mark outlives the countdown, so a render lost before it starts
# only holds back the next ones for a while.
THUMBNAIL_PENDING_MARGIN = 600


def thumbnail_pending_key(item_id):
    """Return the cache key marking a render queued but not started yet."""
    return f"wopi_thumbnail_pending:{item_id}"


def queue_item_thumbnail(item_id, countdown=0):
    """Queue the thumbnail render of an item, unless one is queued and not started yet.

    The render reads the file when it starts, so it covers every save before that.
    """
    if cache.add(
        thumbnail_pending_key(item_id), True, timeout=countdown + THUMBNAIL_PENDING_MARGIN
    ):
        try:
            generate_item_thumbnail.apply_async((item_id,), countdown=countdown)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Could not queue the thumbnail render of item %s", item_id)
            cache.delete(thumbnail_pending_key(item_id))


@app.task(
    autoretry_for=(ConversionProviderError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def generate_item_thumbnail(item_id):
    """Render the thumbnail of a ready item."""
    # A save from now on needs a render of its own.
    cache.delete(thumbnail_pending_key(item_id))
    try:
        item = models.Item.objects.get(id=item_id)
    except models.Item.DoesNotExist:
        logger.error("generate_item_thumbnail: item %s does not exist, aborting", item_id)
        return

    generate_thumbnail(item)
