"""Tests for the management commands scheduled by celery beat."""

import logging
from datetime import timedelta
from unittest import mock

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

import pytest

from core import factories, models
from core.tasks.management_commands import (
    parse_crontab,
    run_management_command,
    setup_periodic_tasks,
)

pytestmark = pytest.mark.django_db


def test_setup_periodic_tasks_nothing_scheduled_by_default():
    """Nothing is scheduled while the commands are left to external cron jobs."""
    sender = mock.MagicMock()

    setup_periodic_tasks(sender)

    sender.add_periodic_task.assert_not_called()


@pytest.mark.parametrize("value", ["", "   "])
def test_setup_periodic_tasks_blank_schedule_not_scheduled(settings, value):
    """A blank schedule leaves the command unscheduled."""
    settings.CLEAN_PENDING_ITEMS_SCHEDULE = value
    sender = mock.MagicMock()

    setup_periodic_tasks(sender)

    sender.add_periodic_task.assert_not_called()


def test_setup_periodic_tasks_schedules_commands_with_their_args(settings):
    """Each configured command is scheduled with its crontab and arguments."""
    settings.CLEAN_PENDING_ITEMS_SCHEDULE = "5 */6 * * * --hours=24"
    settings.PURGE_DELETED_ITEMS_SCHEDULE = "45 0 * * 1"
    sender = mock.MagicMock()

    setup_periodic_tasks(sender)

    calls = {call.kwargs["name"]: call.args for call in sender.add_periodic_task.call_args_list}
    assert set(calls) == {
        "management command clean_pending_items",
        "management command purge_deleted_items",
    }

    clean_schedule, clean_signature = calls["management command clean_pending_items"]
    assert clean_schedule.minute == {5}
    assert clean_schedule.hour == {0, 6, 12, 18}
    assert clean_signature.task == run_management_command.name
    assert clean_signature.args == ("clean_pending_items", "--hours=24")

    purge_schedule, purge_signature = calls["management command purge_deleted_items"]
    assert purge_schedule.minute == {45}
    assert purge_schedule.hour == {0}
    assert purge_schedule.day_of_week == {1}
    assert purge_signature.args == ("purge_deleted_items",)


@pytest.mark.parametrize(
    "setting_name, value, message",
    [
        ("PURGE_DELETED_ITEMS_SCHEDULE", "0 0 * *", "expected a crontab expression"),
        ("PURGE_DELETED_ITEMS_SCHEDULE", "61 0 * * *", "Invalid crontab"),
        ("PURGE_DELETED_ITEMS_SCHEDULE", "0 0 * * * --hours=48", "unrecognized arguments"),
        ("CLEAN_PENDING_ITEMS_SCHEDULE", "0 0 * * * --days=2", "unrecognized arguments"),
        ("CLEAN_PENDING_ITEMS_SCHEDULE", "0 0 * * * --hours=abc", "invalid int value"),
        ("CLEAN_PENDING_ITEMS_SCHEDULE", "0 0 * * * '--hours=48", "No closing quotation"),
    ],
)
def test_setup_periodic_tasks_invalid_configuration(settings, setting_name, value, message):
    """A misconfiguration is refused instead of silently never running a command."""
    setattr(settings, setting_name, value)
    sender = mock.MagicMock()

    with pytest.raises(ImproperlyConfigured, match=message):
        setup_periodic_tasks(sender)

    sender.add_periodic_task.assert_not_called()


def test_app_ready_refuses_invalid_schedule(settings):
    """An invalid schedule stops the application at startup, not only celery beat."""
    settings.PURGE_DELETED_ITEMS_SCHEDULE = "61 0 * * *"

    with pytest.raises(ImproperlyConfigured, match="Invalid crontab"):
        apps.get_app_config("core").ready()


def test_parse_crontab_standard_field_order():
    """Fields follow the standard crontab order, not celery's argument order."""
    schedule = parse_crontab("1 2 3 4 5")

    assert schedule.minute == {1}
    assert schedule.hour == {2}
    assert schedule.day_of_month == {3}
    assert schedule.month_of_year == {4}
    assert schedule.day_of_week == {5}


def test_run_management_command_passes_args_and_logs_output(caplog):
    """The command runs with the configured arguments and its output is logged."""
    old = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    recent = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.PENDING,
    )
    models.Item.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(hours=9))
    models.Item.objects.filter(pk=recent.pk).update(created_at=timezone.now() - timedelta(hours=7))

    with caplog.at_level(logging.INFO, logger="core.tasks.management_commands"):
        run_management_command("clean_pending_items", "--hours=8")

    # The row is only marked: purge_deleted_items removes it with its stored object
    old.refresh_from_db()
    recent.refresh_from_db()
    assert old.hard_deleted_at is not None
    assert recent.hard_deleted_at is None
    assert "clean_pending_items: Cleaned 1 stale pending item(s)." in caplog.text
