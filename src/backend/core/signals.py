"""
Declare and configure the signals for the impress core application
"""

import time
from functools import partial

from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver

from django_structlog import signals as structlog_signals

from . import models
from .tasks.search import trigger_batch_file_indexer

SUPPORT_READ_PERMISSIONS = ["view_user", "view_item", "view_itemaccess", "view_invitation"]
SUPPORT_GROUPS = {
    "Support read-only": SUPPORT_READ_PERMISSIONS,
    "Support operations": [*SUPPORT_READ_PERMISSIONS, "change_user"],
}


@receiver(signals.post_migrate)
def create_support_groups(sender, using, **kwargs):  # pylint: disable=unused-argument
    """Create the support groups of the admin and reset their permissions."""
    if sender.label != "core":
        return
    # Core is installed before auth, whose own handler has not created them yet
    create_permissions(sender, verbosity=0, using=using)
    for name, codenames in SUPPORT_GROUPS.items():
        group, _created = Group.objects.using(using).get_or_create(name=name)
        group.permissions.set(
            Permission.objects.using(using).filter(
                content_type__app_label="core", codename__in=codenames
            )
        )


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


@receiver(structlog_signals.bind_extra_request_finished_metadata)
def log_api_error_codes(response, log_kwargs, **kwargs):  # pylint: disable=unused-argument
    """Log the codes of the API errors, never their details, which can hold file names."""
    data = getattr(response, "data", None)
    if response.status_code >= 400 and isinstance(data, dict) and "errors" in data:
        log_kwargs["error_codes"] = [error["code"] for error in data["errors"]]
