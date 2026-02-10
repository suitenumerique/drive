"""
Unit tests for the User model
"""

import pytest

from drive.settings import Base


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


def test_drive_public_url_is_noop_when_unset():
    """DRIVE_PUBLIC_URL unset should not introduce surprise failures."""

    class TestSettings(Base):
        """Fake test settings."""

        DRIVE_PUBLIC_URL = None

    TestSettings().post_setup()


def test_drive_public_url_trailing_slash_is_normalized():
    """Trailing slash should be normalized away to avoid duplicate slashes in derivations."""

    class TestSettings(Base):
        """Fake test settings."""

        DRIVE_PUBLIC_URL = "https://drive.example.com/"

    TestSettings().post_setup()
    assert TestSettings.DRIVE_PUBLIC_URL == "https://drive.example.com"


def test_drive_public_url_rejects_query_and_does_not_leak_input():
    """Invalid URLs should fail fast with deterministic error metadata and no-leak messages."""

    class TestSettings(Base):
        """Fake test settings."""

        DRIVE_PUBLIC_URL = "https://drive.example.com/?token=super-secret"

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    message = str(excinfo.value)
    assert "failure_class=config.public_url.invalid" in message
    assert "next_action_hint=" in message
    assert "super-secret" not in message
    assert "token=" not in message


def test_drive_public_url_rejects_http_in_production_posture_without_override():
    """HTTP should be rejected in production posture unless explicitly overridden."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = False
        DRIVE_PUBLIC_URL = "http://drive.example.com"
        DRIVE_ALLOW_INSECURE_HTTP = False

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "failure_class=config.public_url.https_required" in str(excinfo.value)


def test_drive_public_url_allows_http_in_production_posture_with_override():
    """Dev-only override should allow HTTP even when running in production posture."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = False
        DRIVE_PUBLIC_URL = "http://drive.example.com/"
        DRIVE_ALLOW_INSECURE_HTTP = True

    TestSettings().post_setup()
    assert TestSettings.DRIVE_PUBLIC_URL == "http://drive.example.com"
