"""
Declare and configure the signals for the impress core application
"""

from functools import partial

from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from . import models
from .storage.cache import invalidate_storage_used_cache
from .tasks.search import trigger_batch_file_indexer

# Item fields whose update can change the storage used by a user.
STORAGE_USED_FIELDS = {"size", "creator", "creator_id", "hard_deleted_at"}


@receiver(signals.post_save, sender=models.Item)
def file_post_save(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Asynchronous call to the document indexer at the end of the transaction.
    Note : Within the transaction we can have an empty content and a serialization
    error.
    """
    transaction.on_commit(partial(trigger_batch_file_indexer, instance))


@receiver(signals.post_save, sender=models.Item)
def item_post_save_invalidate_storage_used(sender, instance, update_fields, **kwargs):  # pylint: disable=unused-argument
    """
    Invalidate the creator's cached storage usage when an item save may have
    changed it. Bulk queryset updates bypass this signal and must invalidate
    the cache explicitly.
    """
    if update_fields is not None and not STORAGE_USED_FIELDS.intersection(update_fields):
        return
    if instance.creator_id is None:
        return
    transaction.on_commit(partial(invalidate_storage_used_cache, [instance.creator_id]))


@receiver(signals.post_save, sender=models.ItemAccess)
def file_access_post_save(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """
    Asynchronous call to the document indexer at the end of the transaction.
    """
    if not created:
        transaction.on_commit(partial(trigger_batch_file_indexer, instance.item))
