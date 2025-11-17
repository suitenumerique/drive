"""Trigger document indexation using celery task."""

from logging import getLogger

from django.conf import settings
from django.core.cache import cache

from django_redis.cache import RedisCache

from core import models
from core.services.search_indexers import get_file_indexer

from drive.celery_app import app

logger = getLogger(__file__)


def batch_indexer_throttle_acquire(timeout: int = 0, atomic: bool = True):
    """
    Enable the task throttle flag for a delay.
    Uses redis locks if available to ensure atomic changes
    """
    key = "file-batch-indexer-throttle"

    # Redis is used as cache database (not in tests). Use the lock feature here
    # to ensure atomicity of changes to the throttle flag.
    if isinstance(cache, RedisCache) and atomic:
        with cache.locks(key):
            return batch_indexer_throttle_acquire(timeout, atomic=False)

    # Use add() here :
    #   - set the flag and returns true if not exist
    #   - do nothing and return false if exist
    return cache.add(key, 1, timeout=timeout)


@app.task
def file_indexer_task(item_id):
    """Celery Task : Sends indexation query for a document."""
    indexer = get_file_indexer()

    if indexer:
        queryset = models.Item.objects.filter(
            pk=item_id,
            main_workspace=False,
        )

        indexer.index(queryset)
        logger.info("Start file %s indexation", item_id)


@app.task
def batch_file_indexer_task(timestamp):
    """Celery Task : Sends indexation query for a batch of documents."""
    indexer = get_file_indexer()

    if indexer:
        queryset = models.Item.objects.filter(
            updated_at__gte=timestamp,
            main_workspace=False,
        )

        count = indexer.index(queryset)
        logger.info("Indexed %d files", count)


def trigger_batch_file_indexer(item):
    """
    Trigger indexation task with debounce a delay set by the SEARCH_INDEXER_COUNTDOWN setting.

    Args:
        item (Item): The file item instance.
    """
    countdown = int(settings.SEARCH_INDEXER_COUNTDOWN)

    # DO NOT create a task if indexation if disabled
    if not settings.SEARCH_INDEXER_CLASS:
        return

    # Ignore triggres from workspace items created along users
    if item.main_workspace:
        return

    if countdown > 0:
        # Each time this method is called during a countdown, we increment the
        # counter and each task decrease it, so the index be run only once.
        if batch_indexer_throttle_acquire(timeout=countdown):
            logger.info(
                "Add task for batch file indexation from updated_at=%s in %d seconds",
                item.updated_at.isoformat(),
                countdown,
            )

            batch_file_indexer_task.apply_async(
                args=[item.updated_at], countdown=countdown
            )
        else:
            logger.info("Skip task for batch file %s indexation", item.pk)
    else:
        file_indexer_task.apply(args=[item.pk])
