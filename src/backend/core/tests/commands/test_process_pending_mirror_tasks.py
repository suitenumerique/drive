"""Tests for the process_pending_mirror_tasks management command."""

from unittest import mock

from django.core.management import call_command

import pytest

from core.factories import MirrorItemTaskFactory
from core.management.commands.process_pending_mirror_tasks import mirror_file
from core.models import MirrorItemTaskStatusChoices

pytestmark = pytest.mark.django_db


def test_process_pending_mirror_tasks_empty():
    """Test command does nothing when there are no pending tasks."""
    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks")
        mock_delay.assert_not_called()


def test_process_pending_mirror_tasks_enqueues_pending_tasks():
    """Test command enqueues pending tasks up to batch_size."""
    pending_tasks = MirrorItemTaskFactory.create_batch(
        5, status=MirrorItemTaskStatusChoices.PENDING
    )

    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks", batch_size=10)

        assert mock_delay.call_count == 5
        for task in pending_tasks:
            mock_delay.assert_any_call(task.id)


def test_process_pending_mirror_tasks_respects_batch_size():
    """Test command only enqueues up to batch_size tasks."""
    MirrorItemTaskFactory.create_batch(15, status=MirrorItemTaskStatusChoices.PENDING)

    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks", batch_size=10)

        assert mock_delay.call_count == 10


def test_process_pending_mirror_tasks_with_processing_tasks():
    """Test command enqueues only remaining slots when tasks are processing."""
    MirrorItemTaskFactory.create_batch(5, status=MirrorItemTaskStatusChoices.PROCESSING)
    MirrorItemTaskFactory.create_batch(10, status=MirrorItemTaskStatusChoices.PENDING)

    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks", batch_size=10)

        assert mock_delay.call_count == 5


def test_process_pending_mirror_tasks_no_slots_available():
    """Test command doesn't enqueue when no slots available."""
    MirrorItemTaskFactory.create_batch(
        10, status=MirrorItemTaskStatusChoices.PROCESSING
    )
    MirrorItemTaskFactory.create_batch(5, status=MirrorItemTaskStatusChoices.PENDING)

    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks", batch_size=10)

        assert mock_delay.call_count == 0


def test_process_pending_mirror_tasks_exact_slots():
    """Test command when pending tasks exactly match available slots."""
    MirrorItemTaskFactory.create_batch(5, status=MirrorItemTaskStatusChoices.PROCESSING)
    MirrorItemTaskFactory.create_batch(5, status=MirrorItemTaskStatusChoices.PENDING)

    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks", batch_size=10)

        assert mock_delay.call_count == 5


def test_process_pending_mirror_tasks_with_pending_already_retried():
    """Test command when pending tasks already retried, they should be ignored."""

    MirrorItemTaskFactory.create_batch(
        3, status=MirrorItemTaskStatusChoices.PENDING, retries=2
    )
    pending_tasks = MirrorItemTaskFactory.create_batch(
        3, status=MirrorItemTaskStatusChoices.PENDING
    )

    with mock.patch.object(mirror_file, "delay") as mock_delay:
        call_command("process_pending_mirror_tasks")

        assert mock_delay.call_count == 3
        for task in pending_tasks:
            mock_delay.assert_any_call(task.id)
