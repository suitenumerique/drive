"""Send one pending alert batch to the explicitly configured demo PostHog project."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.services.security_posthog import DemoDestination, send_demo_batch


class Command(BaseCommand):
    """Keep manual delivery separate from event analysis and Drive analytics."""

    # These commands operate on files/HTTP only, without Drive database access.
    requires_system_checks = []

    help = "Send one demo PostHog alert batch; requires SECURITY_DEMO_POSTHOG_ENABLED."

    def add_arguments(self, parser):
        """Allow sending a separately processed synthetic dataset."""
        parser.add_argument("--workdir", default=settings.SECURITY_MONITORING_WORKDIR)

    def handle(self, *args, **options):
        """Report only sanitized delivery status and counts, never credentials."""
        if not settings.SECURITY_DEMO_POSTHOG_ENABLED:
            self.stdout.write(json.dumps({"status": "disabled", "sent": 0}))
            return
        try:
            result = send_demo_batch(options["workdir"], DemoDestination.from_settings(settings))
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise CommandError(str(error)) from None
        if result["status"] == "retry":
            raise CommandError(f"{result['error']}; retry after {result['retry_seconds']} seconds")
        self.stdout.write(json.dumps(result))
