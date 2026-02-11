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
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    TestSettings().post_setup()


def test_drive_public_url_trailing_slash_is_normalized():
    """Trailing slash should be normalized away to avoid duplicate slashes in derivations."""

    class TestSettings(Base):
        """Fake test settings."""

        DRIVE_PUBLIC_URL = "https://drive.example.com/"
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    TestSettings().post_setup()
    assert TestSettings.DRIVE_PUBLIC_URL == "https://drive.example.com"


def test_drive_public_url_rejects_query_and_does_not_leak_input():
    """Invalid URLs should fail fast with deterministic error metadata and no-leak messages."""

    class TestSettings(Base):
        """Fake test settings."""

        DRIVE_PUBLIC_URL = "https://drive.example.com/?token=super-secret"
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    message = str(excinfo.value)
    assert "failure_class=config.public_url.invalid" in message
    assert "next_action_hint=" in message
    assert "super-secret" not in message
    assert "token=" not in message


def test_drive_public_url_rejects_http_in_production_posture_without_override():
    """HTTPS-only posture rejects HTTP."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = False
        SECURE_SSL_REDIRECT = True
        DRIVE_PUBLIC_URL = "http://drive.example.com"
        DRIVE_ALLOW_INSECURE_HTTP = False
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "failure_class=config.public_url.https_required" in str(excinfo.value)


def test_drive_public_url_rejects_http_in_https_only_posture_even_with_override():
    """HTTPS-only posture should reject HTTP even if the override is set."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = False
        SECURE_SSL_REDIRECT = True
        DRIVE_PUBLIC_URL = "http://drive.example.com/"
        DRIVE_ALLOW_INSECURE_HTTP = True
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "failure_class=config.public_url.https_required" in str(excinfo.value)


def test_drive_public_url_allows_http_in_dev_with_override():
    """Dev-only override allows HTTP when DEBUG=true."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = True
        DRIVE_PUBLIC_URL = "http://drive.example.com/"
        DRIVE_ALLOW_INSECURE_HTTP = True
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    TestSettings().post_setup()
    assert TestSettings.DRIVE_PUBLIC_URL == "http://drive.example.com"


def test_wopi_src_base_url_rejects_http_in_https_only_posture():
    """WOPI public surface must be HTTPS in HTTPS-only posture (no mixed TLS)."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = False
        SECURE_SSL_REDIRECT = True
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = "http://wopi.example.com"
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "Invalid WOPI_SRC_BASE_URL configuration." in str(excinfo.value)
    assert "failure_class=config.public_url.https_required" in str(excinfo.value)


def test_wopi_src_base_url_defaults_to_drive_public_url_when_wopi_enabled(monkeypatch):
    """When WOPI is enabled, WOPI_SRC_BASE_URL defaults to DRIVE_PUBLIC_URL."""

    monkeypatch.setenv("WOPI_VENDORA_DISCOVERY_URL", "http://vendorA/hosting/discovery")

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = True
        SECURE_SSL_REDIRECT = False
        DRIVE_ALLOW_INSECURE_HTTP = True
        DRIVE_PUBLIC_URL = "http://drive.example.com/"

        WOPI_CLIENTS = ["vendorA"]
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    TestSettings().post_setup()
    assert TestSettings.WOPI_SRC_BASE_URL == "http://drive.example.com"


def test_wopi_src_base_url_requires_drive_public_url_when_enabled_and_unset(monkeypatch):
    """WOPI enabled must fail fast if neither DRIVE_PUBLIC_URL nor WOPI_SRC_BASE_URL is set."""

    monkeypatch.setenv("WOPI_VENDORA_DISCOVERY_URL", "http://vendorA/hosting/discovery")

    class TestSettings(Base):
        """Fake test settings."""

        DRIVE_PUBLIC_URL = None
        WOPI_CLIENTS = ["vendorA"]
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = []

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "failure_class=config.wopi.src_base_url.missing" in str(excinfo.value)


def test_oidc_redirect_allowed_hosts_rejects_http_in_https_only_posture():
    """OIDC redirect origins must not contain http:// in HTTPS-only posture."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = False
        SECURE_SSL_REDIRECT = True
        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None
        OIDC_REDIRECT_ALLOWED_HOSTS = [
            "http://localhost:3000",
            "https://drive.example.com",
        ]

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "Invalid OIDC_REDIRECT_ALLOWED_HOSTS configuration." in str(excinfo.value)
    assert "failure_class=config.allowlist.origin.https_required" in str(excinfo.value)


def test_split_allowlists_derive_and_merge_into_consumers():
    """Canonical values from DRIVE_PUBLIC_URL must be included and additions merged."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = True
        SECURE_SSL_REDIRECT = False
        DRIVE_ALLOW_INSECURE_HTTP = True
        DRIVE_PUBLIC_URL = "http://drive.example.com"

        DRIVE_ALLOWED_REDIRECT_URIS = ["http://other.example.com/callback"]
        DRIVE_ALLOWED_ORIGINS = ["http://sdk.example.com"]
        DRIVE_ALLOWED_HOSTS = ["extra-host.example.com:8443"]

        OIDC_REDIRECT_ALLOWED_HOSTS = [
            "http://legacy.example.com",
            "legacy2.example.com:9443",
        ]
        SDK_CORS_ALLOWED_ORIGINS = ["http://legacy-origin.example.com"]

        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None

    TestSettings().post_setup()

    assert TestSettings.OIDC_REDIRECT_ALLOWED_HOSTS == [
        "drive.example.com",
        "extra-host.example.com:8443",
        "legacy.example.com",
        "legacy2.example.com:9443",
        "other.example.com",
    ]
    assert TestSettings.SDK_CORS_ALLOWED_ORIGINS == [
        "http://drive.example.com",
        "http://legacy-origin.example.com",
        "http://sdk.example.com",
    ]


def test_split_allowlists_fail_fast_no_leak_on_bad_redirect_uri():
    """Invalid allowlist entries should fail fast without leaking the raw value."""

    class TestSettings(Base):
        """Fake test settings."""

        DEBUG = True
        SECURE_SSL_REDIRECT = False
        DRIVE_ALLOW_INSECURE_HTTP = True
        DRIVE_PUBLIC_URL = "http://drive.example.com"

        DRIVE_ALLOWED_REDIRECT_URIS = ["http://other.example.com/cb?token=super-secret"]

        OIDC_REDIRECT_ALLOWED_HOSTS = []
        SDK_CORS_ALLOWED_ORIGINS = []

        WOPI_CLIENTS = []
        WOPI_SRC_BASE_URL = None

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    message = str(excinfo.value)
    assert "Invalid DRIVE_ALLOWED_REDIRECT_URIS configuration." in message
    assert "failure_class=config.allowlist.redirect_uri.invalid" in message
    assert "super-secret" not in message
    assert "token=" not in message


def test_external_api_config_rejects_wildcards_no_leak():
    """EXTERNAL_API must be strict (no wildcards) with deterministic errors."""

    class TestSettings(Base):
        """Fake test settings."""

        OIDC_RESOURCE_SERVER_ENABLED = True
        EXTERNAL_API = {
            "items": {"enabled": True, "actions": ["list", "*"]},
        }

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    message = str(excinfo.value)
    assert "Invalid EXTERNAL_API configuration." in message
    assert "failure_class=config.external_api.action.wildcard" in message


def test_external_api_config_requires_items_for_nested_resources():
    """Nested resources under items require items to be enabled."""

    class TestSettings(Base):
        """Fake test settings."""

        OIDC_RESOURCE_SERVER_ENABLED = True
        EXTERNAL_API = {
            "items": {"enabled": False, "actions": []},
            "item_access": {"enabled": True, "actions": ["list"]},
        }

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert "failure_class=config.external_api.dependency.items_required" in str(
        excinfo.value
    )


def test_external_api_config_dedupes_and_sorts_actions_deterministically():
    """External API actions list should be deterministic (deduped + sorted)."""

    class TestSettings(Base):
        """Fake test settings."""

        OIDC_RESOURCE_SERVER_ENABLED = True
        EXTERNAL_API = {
            "items": {
                "enabled": True,
                "actions": ["retrieve", "list", "list", "children"],
            },
            "users": {"enabled": True, "actions": ["get_me"]},
        }

    TestSettings().post_setup()
    assert TestSettings.EXTERNAL_API["items"]["actions"] == [
        "children",
        "list",
        "retrieve",
    ]
