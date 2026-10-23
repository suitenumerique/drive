"""Tests for the logging configuration."""

import logging
from unittest import mock
from uuid import uuid4


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
    """A request should be summarized, and logged by Django when it fails."""
    client.get("/api/v1.0/unknown/", HTTP_X_REQUEST_ID="migrator-42")

    assert console_logs == [
        {
            "event": "",
            "level": "info",
            "logger": "request.summary",
            "agent": "",
            "errno": 0,
            "lang": "",
            "method": "GET",
            "path": "/api/v1.0/unknown/",
            "rid": "migrator-42",
            "t": mock.ANY,
            "uid": "",
        },
        {
            "event": "Not Found: /api/v1.0/unknown/",
            "level": "warning",
            "logger": "django.request",
            "request": "<WSGIRequest: GET '/api/v1.0/unknown/'>",
            "status_code": 404,
        },
    ]


def test_logging_heartbeat(client, console_logs):
    """A heartbeat should be summarized, with the request id of the previous request."""
    client.get("/api/v1.0/unknown/", HTTP_X_REQUEST_ID="migrator-42")
    console_logs.clear()

    client.get("/__lbheartbeat__/")

    assert console_logs == [
        {
            "event": "",
            "level": "info",
            "logger": "request.summary",
            "agent": "",
            "errno": 0,
            "lang": "",
            "method": "GET",
            "path": "/__lbheartbeat__/",
            "rid": "migrator-42",
            "uid": "",
        }
    ]


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
