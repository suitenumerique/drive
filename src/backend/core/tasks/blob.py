"""Tasks related to blobs."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from core.models import Blob

from drive.celery_app import app

logger = logging.getLogger(__name__)


@app.task
def gc_unreferenced_blob(blob_id):
    """
    Delete a blob that lost its last reference beyond the grace period.

    The row is locked and re-checked inside a transaction so a concurrent
    re-attachment cannot lose content: if the blob got referenced again,
    unreferenced_at is cleared and nothing is deleted.
    """
    grace_cutoff = timezone.now() - timedelta(hours=settings.BLOB_UNREFERENCED_GRACE_HOURS)

    with transaction.atomic():
        try:
            blob = Blob.objects.select_for_update().get(pk=blob_id)
        except Blob.DoesNotExist:
            return

        if blob.unreferenced_at is None or blob.unreferenced_at > grace_cutoff:
            return

        if blob.items.exists():
            # Referenced again in the meantime: cancel the pending deletion.
            blob.unreferenced_at = None
            blob.save(update_fields=["unreferenced_at", "updated_at"])
            return

        try:
            default_storage.delete(blob.file_key)
        except FileNotFoundError:
            # Object already absent: still drop the row.
            pass

        blob.delete()
        logger.info("Garbage-collected unreferenced blob %s (%s)", blob.hash, blob_id)
