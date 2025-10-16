"""Trigger document indexation using celery task."""

from logging import getLogger

from django.conf import settings
from django.core.cache import cache

from django_redis.cache import RedisCache

from core import models
from core.services.search_indexers import (
    get_batch_accesses_by_users_and_teams,
    get_file_indexer,
)

from drive.celery_app import app

logger = getLogger(__file__)


def indexer_throttle_acquire(document_id, timeout=0, atomic=True):
    """
    Enable the task throttle flag for a delay.
    Uses redis locks if available to ensure atomic changes
    """
    key = f"file-indexer-throttle-{document_id}"

    if isinstance(cache, RedisCache) and atomic:
        with cache.locks(key):
            return indexer_throttle_acquire(document_id, timeout, atomic=False)

    # Use add() here :
    #   - set the flag and returns true if not exist
    #   - do nothing and return false if exist
    return cache.add(key, 1, timeout=timeout)


@app.task
def file_indexer_task(item_id):
    """Celery Task : Sends indexation query for a document."""
    indexer = get_file_indexer()

    if indexer is None:
        return

    try:
        item = models.Item.objects.get(
            pk=item_id,
            deleted_at__null=True,
            upload_state=models.ItemUploadStateChoices.READY,
        )
    except models.Item.DoesNotExist:
        # Skip the task if the document does not exist.
        return

    accesses = get_batch_accesses_by_users_and_teams((item.path,))

    data = indexer.serialize_item(item=item, accesses=accesses)

    logger.info("Start file %s indexation", item_id)
    indexer.push(data)


def trigger_file_indexer(item):
    """
    Trigger indexation task with debounce a delay set by the SEARCH_INDEXER_COUNTDOWN setting.

    Args:
        item (Item): The file item instance.
    """
    countdown = settings.SEARCH_INDEXER_COUNTDOWN

    # DO NOT create a task if indexation if disabled
    if not settings.SEARCH_INDEXER_CLASS:
        return

    # Each time this method is called during a countdown, we increment the
    # counter and each task decrease it, so the index be run only once.
    if indexer_throttle_acquire(item.pk, timeout=countdown):
        logger.info(
            "Add task for file %s indexation in %.2f seconds",
            item.pk,
            countdown,
        )

        file_indexer_task.apply_async(args=[item.pk], countdown=countdown)
    else:
        logger.info("Skip task for file %s indexation", item.pk)
