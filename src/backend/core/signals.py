"""
Declare and configure the signals for the impress core application
"""

import time
from functools import partial

from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from django_structlog import signals as structlog_signals

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


@receiver(structlog_signals.bind_extra_request_metadata)
def start_request_timer(request, **kwargs):  # pylint: disable=unused-argument
    """Record when the request started, to log its duration when it finishes."""
    request.started_at = time.monotonic()


@receiver(structlog_signals.bind_extra_request_finished_metadata)
def log_request_duration(request, log_kwargs, **kwargs):  # pylint: disable=unused-argument
    """Log the duration of the request with its end."""
    log_kwargs["duration_ms"] = round((time.monotonic() - request.started_at) * 1000)
