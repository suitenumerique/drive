"""Tests for the celery application."""

from importlib import import_module
from unittest import mock

import pytest

from drive.celery_app import WorkerHeartbeatStep, app


@pytest.fixture(name="heartbeat_file")
def fixture_heartbeat_file(tmp_path, monkeypatch):
    """Point the worker heartbeat to a temporary file."""
    path = tmp_path / "celery_worker_heartbeat"
    # The drive package shadows its celery_app module with the celery app
    monkeypatch.setattr(import_module("drive.celery_app"), "WORKER_HEARTBEAT_FILE", path)
    return path


def test_celery_app_worker_heartbeat_step_registered():
    """The heartbeat step should run in every worker."""
    assert WorkerHeartbeatStep in app.steps["worker"]


def test_celery_app_worker_heartbeat_start(heartbeat_file):
    """Starting the worker should touch the heartbeat file and keep touching it."""
    worker = mock.Mock()
    step = WorkerHeartbeatStep(worker)

    step.start(worker)

    assert heartbeat_file.exists()
    worker.timer.call_repeatedly.assert_called_once_with(10, heartbeat_file.touch)


def test_celery_app_worker_heartbeat_stop(heartbeat_file):
    """Stopping the worker should cancel the timer and remove the heartbeat file."""
    worker = mock.Mock()
    step = WorkerHeartbeatStep(worker)
    step.start(worker)

    step.stop(worker)

    worker.timer.call_repeatedly.return_value.cancel.assert_called_once_with()
    assert not heartbeat_file.exists()
