"""Run one bounded security-monitoring batch manually, before enabling Beat."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.services.security_bridge import process_batch
from core.services.security_rules import load_rules


class Command(BaseCommand):
    """Accept raw events or already analyzed alerts as JSONL."""

    # These commands operate on files/HTTP only, without Drive database access.
    requires_system_checks = []

    help = (
        "Process one JSONL batch and write local alert/PostHog exports; sends no network traffic."
    )

    def add_arguments(self, parser):
        """Allow experiments without changing application settings."""
        parser.add_argument("--input", default=settings.SECURITY_MONITORING_INPUT)
        parser.add_argument("--workdir", default=settings.SECURITY_MONITORING_WORKDIR)
        parser.add_argument("--rules", default=settings.SECURITY_MONITORING_RULES)
        parser.add_argument(
            "--batch-size", type=int, default=settings.SECURITY_MONITORING_BATCH_SIZE
        )
        parser.add_argument(
            "--alerts-stdout",
            action="store_true",
            help="Print alert JSONL on stdout; batch summary goes to stderr.",
        )

    def handle(self, *args, **options):
        """Execute and report counts, never raw log contents."""
        try:
            result = process_batch(
                options["input"],
                options["workdir"],
                load_rules(options["rules"]),
                options["batch_size"],
                settings.SECURITY_MONITORING_MAX_LINE_BYTES,
            )
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CommandError(str(error)) from error
        if options["alerts_stdout"]:
            if "batch" in result:
                output = Path(options["workdir"]) / "batches" / f"{result['batch']}.alerts.jsonl"
                self.stdout.write(output.read_text(encoding="utf-8"), ending="")
            self.stderr.write(json.dumps(result))
        else:
            self.stdout.write(json.dumps(result))
