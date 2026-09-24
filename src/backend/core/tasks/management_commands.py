"""Run management commands on a schedule with celery beat."""

import logging
from io import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command, get_commands

from celery import Celery
from celery.schedules import crontab

from drive.celery_app import app

logger = logging.getLogger(__name__)


def parse_crontab(expression):
    """Build a celery schedule from a standard crontab expression (m h dom mon dow)."""
    fields = expression.split()
    if len(fields) != 5:
        raise ImproperlyConfigured(
            f"Invalid crontab {expression!r}: expected 5 fields (m h dom mon dow)."
        )
    minute, hour, day_of_month, month_of_year, day_of_week = fields
    try:
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )
    except ValueError as error:
        raise ImproperlyConfigured(f"Invalid crontab {expression!r}: {error}") from error


def get_periodic_management_commands():
    """
    Validate PERIODIC_MANAGEMENT_COMMANDS and return (name, schedule, args) tuples, so
    that a misconfiguration fails loudly instead of silently never running a command.
    """
    available_commands = get_commands()
    periodic_commands = []
    for name, config in settings.PERIODIC_MANAGEMENT_COMMANDS.items():
        if name not in available_commands:
            raise ImproperlyConfigured(f"PERIODIC_MANAGEMENT_COMMANDS: unknown command {name!r}.")
        if not isinstance(config, dict) or "schedule" not in config:
            raise ImproperlyConfigured(
                f"PERIODIC_MANAGEMENT_COMMANDS: {name!r} requires a 'schedule'."
            )
        if unexpected := set(config) - {"schedule", "args"}:
            raise ImproperlyConfigured(
                f"PERIODIC_MANAGEMENT_COMMANDS: unexpected keys {sorted(unexpected)} for {name!r}."
            )
        args = config.get("args", [])
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ImproperlyConfigured(
                f"PERIODIC_MANAGEMENT_COMMANDS: 'args' of {name!r} must be a list of strings."
            )
        periodic_commands.append((name, parse_crontab(config["schedule"]), args))

    return periodic_commands


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    """Schedule the management commands listed in PERIODIC_MANAGEMENT_COMMANDS."""
    for name, schedule, args in get_periodic_management_commands():
        sender.add_periodic_task(
            schedule,
            run_management_command.s(name, *args),
            name=f"management command {name}",
            serializer="json",
        )


@app.task
def run_management_command(name, *args):
    """Run a management command and send its output to the logs."""
    output = StringIO()
    call_command(name, *args, stdout=output, stderr=output)
    logger.info("%s: %s", name, output.getvalue().strip())
