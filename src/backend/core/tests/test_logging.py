"""Tests for the logging configuration."""

import logging


def test_logging_core_logger(console_logs):
    """Logs of the core application should be written to the console."""
    logging.getLogger("core.api").warning("item creation refused")

    assert len(console_logs) == 1
    assert console_logs[0].endswith(" core.api WARNING item creation refused")


def test_logging_request(client, console_logs):
    """A request should be summarized, and logged by Django when it fails."""
    client.get("/api/v1.0/unknown/", HTTP_X_REQUEST_ID="migrator-42")

    assert len(console_logs) == 2
    assert console_logs[0].endswith(" request.summary INFO ")
    assert console_logs[1].endswith(" django.request WARNING Not Found: /api/v1.0/unknown/")


def test_logging_heartbeat(client, console_logs):
    """A heartbeat should be summarized."""
    client.get("/__lbheartbeat__/")

    assert len(console_logs) == 1
    assert console_logs[0].endswith(" request.summary INFO ")
