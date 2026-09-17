"""Send one explicit digest without enabling the periodic sender."""

import json
import smtplib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.services.security_digest import send_digest


class Command(BaseCommand):
    """Manual opt-in with explicit recipients or the configured recipient list."""

    requires_system_checks = []
    help = "Send pending analyzed alerts through the configured Django mail backend."

    def add_arguments(self, parser):
        parser.add_argument("--workdir", default=settings.SECURITY_MONITORING_WORKDIR)
        parser.add_argument("--to", nargs="+", default=settings.SECURITY_DIGEST_RECIPIENTS)
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        try:
            result = send_digest(options["workdir"], options["to"], options["limit"])
        except (OSError, smtplib.SMTPException, ValueError, ValidationError) as error:
            raise CommandError(
                f"Digest not sent ({type(error).__name__}); cursor unchanged"
            ) from None
        self.stdout.write(json.dumps(result))
