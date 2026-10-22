"""
Declare and configure the signals for the impress core application
"""

from functools import partial

from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from . import models
from .services.announcements import invalidate_announcements_cache
from .tasks.search import trigger_batch_file_indexer


@receiver(signals.post_save, sender=models.Item)
def file_post_save(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Asynchronous call to the document indexer at the end of the transaction.
    Note : Within the transaction we can have an empty content and a serialization
    error.
    """
    transaction.on_commit(partial(trigger_batch_file_indexer, instance))


@receiver(signals.post_save, sender=models.ItemAccess)
def file_access_post_save(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """
    Asynchronous call to the document indexer at the end of the transaction.
    """
    if not created:
        transaction.on_commit(partial(trigger_batch_file_indexer, instance.item))


ANNOUNCEMENT_TRANSLATION = models.Announcement._meta.get_field(  # noqa: SLF001
    "translations"
).related_model


@receiver(signals.post_save, sender=models.Announcement)
@receiver(signals.post_delete, sender=models.Announcement)
@receiver(signals.post_save, sender=ANNOUNCEMENT_TRANSLATION)
@receiver(signals.post_delete, sender=ANNOUNCEMENT_TRANSLATION)
def announcement_changed(sender, **kwargs):  # pylint: disable=unused-argument
    """Publish the changes of the announcements or their translations right away."""
    invalidate_announcements_cache()
