"""Tests for the management commands scheduled by celery beat."""

import logging
from datetime import timedelta
from unittest import mock

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


def test_setup_periodic_tasks_schedules_commands_with_their_args(settings):
    """Each configured command is scheduled with its crontab and arguments."""
    settings.PERIODIC_MANAGEMENT_COMMANDS = {
        "clean_pending_items": {"schedule": "5 */6 * * *", "args": ["--hours=24"]},
        "purge_deleted_items": {"schedule": "45 0 * * 1"},
    }
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
    "config, message",
    [
        ({"unknown_command": {"schedule": "* * * * *"}}, "unknown command"),
        ({"purge_deleted_items": {}}, "requires a 'schedule'"),
        ({"purge_deleted_items": "45 0 * * *"}, "requires a 'schedule'"),
        ({"purge_deleted_items": {"schedule": "* * * * *", "arg": []}}, "unexpected keys"),
        ({"purge_deleted_items": {"schedule": "* * * * *", "args": "--x"}}, "list of strings"),
        ({"purge_deleted_items": {"schedule": "0 0 * *"}}, "expected 5 fields"),
        ({"purge_deleted_items": {"schedule": "61 0 * * *"}}, "Invalid crontab"),
    ],
)
def test_setup_periodic_tasks_invalid_configuration(settings, config, message):
    """A misconfiguration is refused instead of silently never running a command."""
    settings.PERIODIC_MANAGEMENT_COMMANDS = config
    sender = mock.MagicMock()

    with pytest.raises(ImproperlyConfigured, match=message):
        setup_periodic_tasks(sender)

    sender.add_periodic_task.assert_not_called()


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

    assert not models.Item.objects.filter(pk=old.pk).exists()
    assert models.Item.objects.filter(pk=recent.pk).exists()
    assert "clean_pending_items: Cleaned 1 stale pending item(s)." in caplog.text
