"""Signal receivers of the wopi app."""

from functools import partial

from django.conf import settings
from django.db import transaction
from django.dispatch import receiver

from core.signals import item_file_ready
from wopi.conversion.thumbnails import thumbnail_clients
from wopi.tasks.thumbnails import queue_item_thumbnail


@receiver(item_file_ready)
def queue_thumbnail_on_file_ready(sender, item, **kwargs):  # pylint: disable=unused-argument
    """Render the thumbnail of a file once its ready state is committed.

    A file without a thumbnail gets one right away. A file with one is re-rendered after
    WOPI_THUMBNAIL_DEBOUNCE seconds, so the saves of an editing session share a render.
    """
    if not any(thumbnail_clients()):
        return
    countdown = settings.WOPI_THUMBNAIL_DEBOUNCE if item.thumbnail_updated_at else 0
    transaction.on_commit(partial(queue_item_thumbnail, str(item.id), countdown))
