"""Periodic entry point; processing itself also works without Celery."""

import logging

from django.conf import settings

from core.services.security_bridge import process_batch, publish_alerts
from core.services.security_digest import send_digest
from core.services.security_posthog import DemoDestination, send_demo_batch
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


@app.task(ignore_result=True)
def send_security_alerts():
    """Deliver pending analyzed alerts to the explicitly configured demo project."""
    if not settings.SECURITY_DEMO_POSTHOG_ENABLED:
        return {"status": "disabled", "sent": 0}
    result = send_demo_batch(
        settings.SECURITY_MONITORING_WORKDIR, DemoDestination.from_settings(settings)
    )
    if result["status"] == "retry":
        logger.warning("Demo PostHog delivery: %s", result)
    else:
        logger.info("Demo PostHog delivery: %s", result)
    return result


@app.task(ignore_result=True)
def send_security_digest():
    """Deliver an optional digest; failures retain the independent delivery cursor."""
    if not settings.SECURITY_DIGEST_ENABLED:
        return {"status": "disabled", "sent": 0}
    return send_digest(settings.SECURITY_MONITORING_WORKDIR, settings.SECURITY_DIGEST_RECIPIENTS)
