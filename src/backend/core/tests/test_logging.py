"""Tests for the logging configuration."""

import hashlib
import logging
from io import BytesIO
from unittest import mock
from uuid import uuid4

from django.core.cache import cache
from django.core.files.storage import default_storage

import pytest
import structlog
from celery.app.log import Logging
from celery.signals import before_task_publish, task_prerun
from rest_framework.test import APIClient

from core import factories
from core.models import ItemTypeChoices, ItemUploadStateChoices, RoleChoices
from core.tasks.item import process_item_purge
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY

from drive.celery_app import app as celery_app

pytestmark = pytest.mark.django_db


def test_logging_core_logger(console_logs):
    """Logs of the core application should be written to the console."""
    logging.getLogger("core.api").warning("item creation refused")

    assert console_logs == [
        {"event": "item creation refused", "level": "warning", "logger": "core.api"}
    ]


def test_logging_structlog_event(console_logs):
    """A structlog event should be written with its fields and positional arguments."""
    structlog.get_logger("core.api").warning("item %s creation refused", "x", reason="quota")

    assert console_logs == [
        {
            "event": "item x creation refused",
            "level": "warning",
            "logger": "core.api",
            "reason": "quota",
        }
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


def test_logging_request_wopi_session(console_logs):
    """A WOPI session should be logged with the same id from its token to the editor requests."""
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            "mimetypes": {
                "application/vnd.oasis.opendocument.text": {
                    "launch_url": "https://vendorA.com/launch_url",
                    "client": "vendorA",
                },
            },
            "extensions": {},
            "vendorA": {"proof_keys": {}},
        },
    )
    user = factories.UserFactory()
    item = factories.ItemFactory(
        type=ItemTypeChoices.FILE,
        filename="wopi_test.odt",
        mimetype="application/vnd.oasis.opendocument.text",
        update_upload_state=ItemUploadStateChoices.READY,
        users=[(user, RoleChoices.EDITOR)],
    )
    default_storage.save(item.file_key, BytesIO(b"my prose"))
    client = APIClient()
    client.force_login(user)

    data = client.get(f"/api/v1.0/items/{item.id}/wopi/").json()
    APIClient().get(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
        HTTP_X_WOPI_SESSIONID="editor-session-1",
    )

    token_hash = hashlib.sha256(data["access_token"].encode()).hexdigest()[:12]
    assert f"&usid={token_hash}&" in data["launch_url"]
    finished = [line for line in console_logs if line["event"] == "request_finished"]
    assert finished[0]["request"] == f"GET /api/v1.0/items/{item.id}/wopi/"
    assert finished[0]["wopi_token_hash"] == token_hash
    assert "wopi_client_session_id" not in finished[0]
    assert finished[1]["request"] == f"GET /api/v1.0/wopi/files/{item.id}/"
    assert finished[1]["wopi_token_hash"] == token_hash
    assert finished[1]["wopi_client_session_id"] == "editor-session-1"


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

    assert console_logs == [
        {"event": "Task succeeded", "level": "info", "logger": "celery.app.trace"}
    ]


def test_logging_celery_task_arguments(console_logs):
    """Celery logs should be written without the arguments of the tasks."""
    context = {"id": "task-1", "name": "core.tasks.item.rename_file", "args": "['secret']"}

    logging.getLogger("celery.worker.strategy").info(
        "Task %(name)s[%(id)s] received", context, extra={"data": context}
    )

    assert console_logs == [
        {
            "event": "Task core.tasks.item.rename_file[task-1] received",
            "level": "info",
            "logger": "celery.worker.strategy",
        }
    ]


def test_logging_celery_task(console_logs):
    """Logs of a task should carry the request id of the request that sent it."""
    task = process_item_purge
    # Start the steps of a worker, which hold its signal receivers
    _worker_steps = [step(mock.Mock()) for step in celery_app.steps["worker"]]
    headers = {}
    structlog.contextvars.bind_contextvars(request_id="migrator-42")
    before_task_publish.send(sender=task.name, headers=headers, body=None)

    # The worker runs the task in another process, with the message headers
    structlog.contextvars.clear_contextvars()
    task.push_request(**headers)
    try:
        task_prerun.send(sender=task, task_id="task-1", task=task, args=(), kwargs={})
        logging.getLogger("core.tasks.item").info("Processing item purge")
    finally:
        task.pop_request()

    assert console_logs == [
        {
            "event": "task_started",
            "level": "info",
            "logger": "django_structlog.celery.receivers",
            "request_id": "migrator-42",
            "task": "core.tasks.item.process_item_purge",
            "task_id": "task-1",
        },
        {
            "event": "Processing item purge",
            "level": "info",
            "logger": "core.tasks.item",
            "request_id": "migrator-42",
            "task_id": "task-1",
        },
    ]
