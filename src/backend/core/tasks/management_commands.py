"""Run management commands on a schedule with celery beat."""

import logging
import shlex
from io import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import (
    CommandError,
    call_command,
    get_commands,
    load_command_class,
)

from celery import Celery
from celery.schedules import crontab

from drive.celery_app import app

logger = logging.getLogger(__name__)

# Commands that can be scheduled, with the setting holding their schedule
PERIODIC_COMMAND_SETTINGS = {
    "clean_pending_items": "CLEAN_PENDING_ITEMS_SCHEDULE",
    "purge_deleted_items": "PURGE_DELETED_ITEMS_SCHEDULE",
}


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


def parse_schedule(setting_name, name, value):
    """
    Split a schedule setting into a celery schedule and the command arguments: the
    first 5 fields are a crontab expression, the remaining ones the arguments.
    """
    try:
        fields = shlex.split(value)
    except ValueError as error:
        raise ImproperlyConfigured(f"{setting_name}: {error}.") from error
    if len(fields) < 5:
        raise ImproperlyConfigured(
            f"{setting_name}: expected a crontab expression (m h dom mon dow) "
            "followed by the command arguments."
        )
    schedule = parse_crontab(" ".join(fields[:5]))
    args = fields[5:]

    # Parse the arguments now: a typo would otherwise only fail when the command runs
    command = load_command_class(get_commands()[name], name)
    try:
        command.create_parser("manage.py", name).parse_args(args)
    except CommandError as error:
        raise ImproperlyConfigured(f"{setting_name}: {error}") from error

    return schedule, args


def get_periodic_management_commands():
    """
    Validate the schedule settings and return (name, schedule, args) tuples, so that a
    misconfiguration fails loudly instead of silently never running a command.
    """
    periodic_commands = []
    for name, setting_name in PERIODIC_COMMAND_SETTINGS.items():
        value = getattr(settings, setting_name)
        if not value or not value.strip():
            continue
        schedule, args = parse_schedule(setting_name, name, value)
        periodic_commands.append((name, schedule, args))

    return periodic_commands


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    """Schedule the management commands whose schedule setting is set."""
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
