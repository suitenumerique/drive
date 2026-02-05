"""Module test wopi settings dynamic configuration"""

import pytest

from drive.settings import Base


def test_valid_wopi_configuration(monkeypatch):
    """Valid WOPI configuration should be correctly loaded."""
    monkeypatch.setenv(
        "WOPI_VENDORA_DISCOVERY_URL", "https://vendorA.com/hosting/discovery"
    )

    monkeypatch.setenv(
        "WOPI_VENDORB_DISCOVERY_URL", "https://vendorB.com/hosting/discovery"
    )

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = ["vendorA", "vendorB"]
        WOPI_CLIENTS_CONFIGURATION = {}

    TestSettings.post_setup()

    assert TestSettings.WOPI_CLIENTS_CONFIGURATION == {
        "vendorA": {
            "discovery_url": "https://vendorA.com/hosting/discovery",
            "mimetypes": {},
            "extensions": {},
            "options": {},
        },
        "vendorB": {
            "discovery_url": "https://vendorB.com/hosting/discovery",
            "mimetypes": {},
            "extensions": {},
            "options": {},
        },
    }


def test_wopi_configuration_missing_discovery_url():
    """
    When a WOPI client is missing the discovery url configuration, a ValueError should be
    raised.
    """

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = ["vendorA"]
        WOPI_CLIENTS_CONFIGURATION = {}

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert str(excinfo.value) == (
        "Value 'WOPI_VENDORA_DISCOVERY_URL' is required to be set as the environment"
        " variable 'WOPI_VENDORA_DISCOVERY_URL'"
    )


def test_no_wopi_configuration():
    """Without WOPI clients, the configuration should be empty."""

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = []
        WOPI_CLIENTS_CONFIGURATION = {}

    TestSettings.post_setup()

    assert not TestSettings.WOPI_CLIENTS_CONFIGURATION
