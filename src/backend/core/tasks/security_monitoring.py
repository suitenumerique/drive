"""Periodic entry point; processing itself also works without Celery."""

import logging

from django.conf import settings

from core.services.security_bridge import process_batch, publish_alerts
from core.services.security_rules import load_rules

from drive.celery_app import app

logger = logging.getLogger(__name__)


@app.task(ignore_result=True)
def process_security_logs():
    """Run one bounded batch. Next Beat tick retries after a failure."""
    if not settings.SECURITY_MONITORING_ENABLED:
        return {"status": "disabled"}
    result = process_batch(
        settings.SECURITY_MONITORING_INPUT,
        settings.SECURITY_MONITORING_WORKDIR,
        load_rules(settings.SECURITY_MONITORING_RULES),
        settings.SECURITY_MONITORING_BATCH_SIZE,
        settings.SECURITY_MONITORING_MAX_LINE_BYTES,
    )
    result["published"] = publish_alerts(settings.SECURITY_MONITORING_WORKDIR)
    logger.info("Security monitoring batch: %s", result)
    return result
