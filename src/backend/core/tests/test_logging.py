"""Tests for the logging configuration."""

import logging
from unittest import mock
from uuid import uuid4

import pytest
from celery.app.log import Logging
from rest_framework.test import APIClient

from core import factories
from core.models import ItemTypeChoices

from drive.celery_app import app as celery_app

pytestmark = pytest.mark.django_db


def test_logging_core_logger(console_logs):
    """Logs of the core application should be written to the console."""
    logging.getLogger("core.api").warning("item creation refused")

    assert console_logs == [
        {"event": "item creation refused", "level": "warning", "logger": "core.api"}
    ]


def test_logging_extra_fields(console_logs):
    """The extra fields of a log should be written as text."""
    item_id = uuid4()

    logging.getLogger("core.api").warning("item creation refused", extra={"item_id": item_id})

    assert console_logs == [
        {
            "event": "item creation refused",
            "level": "warning",
            "logger": "core.api",
            "item_id": str(item_id),
        }
    ]


def test_logging_request(client, console_logs):
    """A request should be logged when it starts and ends."""
    client.get("/api/v1.0/unknown/", HTTP_X_REQUEST_ID="migrator-42")

    assert console_logs == [
        {
            "event": "request_started",
            "level": "info",
            "logger": "django_structlog.middlewares.request",
            "request": "GET /api/v1.0/unknown/",
            "request_id": "migrator-42",
            "user_agent": None,
            "user_id": None,
        },
        {
            "event": "request_finished",
            "level": "warning",
            "logger": "django_structlog.middlewares.request",
            "code": 404,
            "duration_ms": mock.ANY,
            "request": "GET /api/v1.0/unknown/",
            "request_id": "migrator-42",
            "user_id": None,
        },
    ]
    assert isinstance(console_logs[1]["duration_ms"], int)


def test_logging_request_user(client, console_logs):
    """A request should be logged with the id of its user."""
    user = factories.UserFactory()
    client.force_login(user)

    client.get("/api/v1.0/users/me/", HTTP_X_REQUEST_ID="migrator-42")

    assert console_logs[-1] == {
        "event": "request_finished",
        "level": "info",
        "logger": "django_structlog.middlewares.request",
        "code": 200,
        "duration_ms": mock.ANY,
        "request": "GET /api/v1.0/users/me/",
        "request_id": "migrator-42",
        "user_id": str(user.pk),
    }


def test_logging_request_api_error(console_logs):
    """A request refused by the API should be logged with its error codes."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post("/api/v1.0/items/", {"type": ItemTypeChoices.FILE}, format="json")

    assert response.status_code == 400
    assert console_logs[-1] == {
        "event": "request_finished",
        "level": "warning",
        "logger": "django_structlog.middlewares.request",
        "code": 400,
        "duration_ms": mock.ANY,
        "error_codes": ["item_create_file_filename_required"],
        "request": "POST /api/v1.0/items/",
        "request_id": mock.ANY,
        "user_id": str(user.pk),
    }


def test_logging_request_exception(client, console_logs):
    """A request that raises should be logged with its traceback."""
    client.raise_request_exception = False
    user = factories.UserFactory()
    client.force_login(user)

    with mock.patch(
        "core.api.viewsets.UserViewSet.get_serializer", side_effect=ValueError("unknown user")
    ):
        client.get("/api/v1.0/users/me/", HTTP_X_REQUEST_ID="migrator-42")

    assert console_logs[1:] == [
        {
            "event": "request_failed",
            "level": "error",
            "logger": "django_structlog.middlewares.request",
            "code": 500,
            "exception": mock.ANY,
            "request": "GET /api/v1.0/users/me/",
            "request_id": "migrator-42",
            "user_id": str(user.pk),
        },
    ]
    assert console_logs[1]["exception"].endswith("\nValueError: unknown user")


def test_logging_heartbeat(client, console_logs):
    """A heartbeat should not be logged."""
    client.get("/__lbheartbeat__/")

    assert console_logs == []


def test_logging_exception(console_logs):
    """An exception should be logged with its traceback."""
    try:
        raise ValueError("unknown item")
    except ValueError:
        logging.getLogger("core.api").exception("item creation failed")

    assert console_logs == [
        {
            "event": "item creation failed",
            "level": "error",
            "logger": "core.api",
            "exception": mock.ANY,
        }
    ]
    assert console_logs[0]["exception"].startswith("Traceback ")
    assert console_logs[0]["exception"].endswith("\nValueError: unknown item")


def test_logging_celery_worker(console_logs):
    """Celery workers should write the logs to the console."""
    root = logging.getLogger()
    with (
        mock.patch.object(root, "handlers", list(root.handlers)),
        mock.patch.object(Logging, "_setup", False),
    ):
        celery_app.log.setup_logging_subsystem(loglevel="INFO")
        logging.getLogger("celery.app.trace").info("Task succeeded")

    assert console_logs == []
