"""
Unit tests for the User model
"""

import logging
from unittest import mock
from uuid import uuid4

import pytest
from celery.app.log import Logging
from configurations import values

from drive.celery_app import app as celery_app
from drive.settings import Base, Feature, LoadTest, PreProduction, Production, Staging


def test_invalid_settings_oidc_email_configuration():
    """
    The OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION and OIDC_ALLOW_DUPLICATE_EMAILS settings
    should not be both set to True simultaneously.
    """

    class TestSettings(Base):
        """Fake test settings."""

        OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION = True
        OIDC_ALLOW_DUPLICATE_EMAILS = True

    # The validation is performed during post_setup
    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    # Check the exception message
    assert str(excinfo.value) == (
        "Both OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION and "
        "OIDC_ALLOW_DUPLICATE_EMAILS cannot be set to True simultaneously. "
    )


def test_load_e2e_urls_is_not_environment_configurable():
    """
    LOAD_E2E_URLS exposes credential-less login endpoints: it must be a plain
    literal so it can never be flipped through an environment variable.
    """
    assert Base.LOAD_E2E_URLS is False
    assert not isinstance(Base.LOAD_E2E_URLS, values.Value)


@pytest.mark.parametrize("configuration", [Production, Feature, Staging, PreProduction])
def test_load_e2e_urls_disabled_on_production_configurations(configuration):
    """No production-facing configuration may expose the e2e auth endpoints."""
    assert configuration.LOAD_E2E_URLS is False


def test_load_e2e_urls_refused_outside_allowlist():
    """
    Even if a configuration sets LOAD_E2E_URLS to True, the application must
    refuse to start unless the configuration is explicitly allowlisted.
    """

    class EvilProduction(Production):
        """Fake production settings trying to expose the e2e auth endpoints."""

        LOAD_E2E_URLS = True

    with pytest.raises(ValueError) as excinfo:
        EvilProduction().post_setup()

    assert str(excinfo.value) == (
        "LOAD_E2E_URLS must never be enabled on the EvilProduction configuration."
    )


def test_load_e2e_urls_allowed_on_load_test_configuration():
    """The dedicated LoadTest configuration exposes the e2e auth endpoints."""
    assert LoadTest.LOAD_E2E_URLS is True
    LoadTest().post_setup()


def test_psycopg_pool_disabled_by_default():
    """The psycopg pool should not be configured unless DB_PSYCOPG_POOL_ENABLED is set."""

    class TestSettings(Base):
        """Fake test settings with their own database configuration."""

        DATABASES = {"default": {"OPTIONS": {"sslmode": "require"}}}

    TestSettings().post_setup()

    assert TestSettings.DATABASES["default"]["OPTIONS"] == {"sslmode": "require"}


def test_psycopg_pool_enabled(monkeypatch):
    """Enabling DB_PSYCOPG_POOL_ENABLED should add the pool to the existing database options."""
    monkeypatch.setenv("DB_PSYCOPG_POOL_ENABLED", "True")
    monkeypatch.setenv("DB_PSYCOPG_POOL_MAX_SIZE", "10")

    class TestSettings(Base):
        """Fake test settings with their own database configuration."""

        DATABASES = {"default": {"OPTIONS": {"sslmode": "require"}}}

    TestSettings().post_setup()

    assert TestSettings.DATABASES["default"]["OPTIONS"] == {
        "sslmode": "require",
        "pool": {"min_size": 4, "max_size": 10, "timeout": 3},
    }


def test_logging_request_id(client, console_logs):
    """Logs emitted during a request should carry its X-Request-ID header."""
    client.get("/api/v1.0/unknown/", HTTP_X_REQUEST_ID="migrator-42")

    log = console_logs[-1]
    assert log["Type"] == "django.request"
    assert log["Fields"]["rid"] == "migrator-42"
    assert log["Fields"]["msg"] == "Not Found: /api/v1.0/unknown/"


def test_logging_request_id_heartbeat(client, console_logs):
    """Heartbeat logs should not carry the X-Request-ID of the previous request."""
    client.get("/api/v1.0/unknown/", HTTP_X_REQUEST_ID="migrator-42")
    console_logs.clear()

    client.get("/__lbheartbeat__/")

    log = console_logs[0]
    assert log["Type"] == "request.summary"
    assert log["Fields"]["path"] == "/__lbheartbeat__/"
    assert log["Fields"]["rid"] is None


def test_logging_core_logger(console_logs):
    """Logs of the core application should be written to the console."""
    logging.getLogger("core.api").warning("item creation refused")

    assert len(console_logs) == 1
    log = console_logs[0]
    assert log["Type"] == "core.api"
    assert log["Logger"] == "drive"
    assert log["Level"] == "WARNING"
    assert log["Severity"] == 4
    assert log["Fields"] == {"msg": "item creation refused", "rid": None}


def test_logging_uuid(console_logs):
    """UUIDs passed to a log should be written as text."""
    user_id = uuid4()

    logging.getLogger("core.api").warning("item creation refused", extra={"uid": user_id})

    assert console_logs[0]["Fields"]["uid"] == str(user_id)


def test_logging_celery_worker(console_logs):
    """Celery workers should write the logs to the console."""
    root = logging.getLogger()
    with (
        mock.patch.object(root, "handlers", list(root.handlers)),
        mock.patch.object(Logging, "_setup", False),
    ):
        celery_app.log.setup_logging_subsystem(loglevel="INFO")
        logging.getLogger("celery.app.trace").info("Task succeeded")

    assert len(console_logs) == 1
    log = console_logs[0]
    assert log["Type"] == "celery.app.trace"
    assert log["Fields"]["msg"] == "Task succeeded"
