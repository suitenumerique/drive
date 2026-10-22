"""
Declare and configure the signals for the impress core application
"""

from functools import partial

from django.core.signals import request_started
from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from dockerflow.logging import request_id_context

from . import models
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


@receiver(request_started, dispatch_uid="core.reset_request_id")
def reset_request_id(**kwargs):  # pylint: disable=unused-argument
    """Forget the request id of the previous request, which heartbeats never replace."""
    request_id_context.set(None)
