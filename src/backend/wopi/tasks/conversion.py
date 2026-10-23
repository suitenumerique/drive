"""Celery tasks for WOPI conversion."""

from django.contrib.auth import get_user_model

import structlog

from core import models
from wopi.conversion.exceptions import ConversionProviderError
from wopi.conversion.services import perform_conversion

from drive.celery_app import app

logger = structlog.get_logger(__name__)

# Seconds to wait before re-checking a source still under malware analysis,
# and how many times to wait before giving up (~10 minutes total, matching the
# frontend polling timeout).
ANALYSIS_RETRY_COUNTDOWN = 30
ANALYSIS_MAX_RETRIES = 20


class ConvertFileTask(app.Task):
    """Celery task base deleting the placeholder when conversion ultimately fails."""

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def on_failure(self, _exc, _task_id, _args, kwargs, _einfo):
        """Hard-delete the placeholder after retries are exhausted."""
        placeholder_id = kwargs.get("converted_item_id")
        if not placeholder_id:
            return

        try:
            placeholder = models.Item.objects.get(id=placeholder_id)
            placeholder.soft_delete()
            placeholder.delete()
        except models.Item.DoesNotExist:
            return


@app.task(
    bind=True,
    base=ConvertFileTask,
    autoretry_for=(ConversionProviderError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def convert_file(self, source_item_id, converted_item_id, user_id):
    """Convert the source item and attach the result to the placeholder."""
    User = get_user_model()  # pylint: disable=invalid-name

    try:
        source = models.Item.objects.get(id=source_item_id)
    except models.Item.DoesNotExist:
        logger.error("file_conversion_source_not_found", item_id=source_item_id)
        return

    try:
        placeholder = models.Item.objects.get(id=converted_item_id)
    except models.Item.DoesNotExist:
        logger.error("file_conversion_placeholder_not_found", item_id=converted_item_id)
        return

    if placeholder.upload_state != models.ItemUploadStateChoices.CONVERTING:
        logger.error(
            "file_conversion_placeholder_not_converting",
            item_id=converted_item_id,
            upload_state=placeholder.upload_state,
        )
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("file_conversion_user_not_found", user_id=user_id)
        return

    if source.upload_state == models.ItemUploadStateChoices.ANALYZING:
        logger.info("file_conversion_postponed", item_id=source_item_id)
        raise self.retry(countdown=ANALYSIS_RETRY_COUNTDOWN, max_retries=ANALYSIS_MAX_RETRIES)

    try:
        perform_conversion(source, placeholder, user)
    except Exception:
        logger.exception("file_conversion_failed", item_id=converted_item_id)
        raise
