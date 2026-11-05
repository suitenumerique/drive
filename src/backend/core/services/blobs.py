"""Helpers to produce blobs outside the client upload flow."""

import hashlib
import logging
from io import BytesIO

from django.core.files.storage import default_storage

from core.models import Blob, ItemUploadStateChoices

logger = logging.getLogger(__name__)


def store_content_as_blob(content: bytes, *, ready: bool = True) -> Blob:
    """
    Write content under its content-addressed key blobs/<sha256> and return the Blob.

    Used by server-side producers (file templates, conversion) and by WOPI PutFile.
    With ready=True the content is server-generated and trusted: a newly created
    blob is READY directly, without antivirus analysis. With ready=False (client
    content), the blob starts ANALYZING. Existing blobs keep their own state.
    """
    digest = hashlib.sha256(content).hexdigest()
    blob, _created = Blob.objects.get_or_create(
        hash=digest,
        defaults={
            "size": len(content),
            "upload_state": (
                ItemUploadStateChoices.READY if ready else ItemUploadStateChoices.ANALYZING
            ),
        },
    )
    if not default_storage.exists(blob.file_key):
        default_storage.save(blob.file_key, BytesIO(content))
    return blob
