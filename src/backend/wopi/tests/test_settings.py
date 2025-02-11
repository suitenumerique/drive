"""Module test wopi settings dynamic configuration"""

import pytest

from drive.settings import Base


def test_valid_wopi_configuration(monkeypatch):
    """Valid WOPI configuration should be correctly loaded."""
    monkeypatch.setenv(
        "WOPI_VENDORA_MIMETYPES",
        "application/vnd.oasis.opendocument.text,application/vnd.oasis.opendocument.spreadsheet",
    )

    monkeypatch.setenv("WOPI_VENDORB_LAUNCH_URL", "https://vendorB.com/launch_url")
    monkeypatch.setenv(
        "WOPI_VENDORB_MIMETYPES", "application/vnd.oasis.opendocument.presentation"
    )

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = ["vendorA", "vendorB"]
        WOPI_CLIENTS_CONFIGURATION = {}

    TestSettings.post_setup()

    assert TestSettings.WOPI_CLIENTS_CONFIGURATION == {
        "vendorA": {
            "launch_url": "https://vendorA.com/launch_url",
            "mimetypes": [
                "application/vnd.oasis.opendocument.text",
                "application/vnd.oasis.opendocument.spreadsheet",
            ],
        },
        "vendorB": {
            "launch_url": "https://vendorB.com/launch_url",
            "mimetypes": ["application/vnd.oasis.opendocument.presentation"],
        },
    }


def test_wopi_configuration_missing_mimetypes(monkeypatch):
    """
    When a WOPI client is missing the mimetypes configuration, a ValueError should be
    raised.
    """
    monkeypatch.setenv("WOPI_VENDORA_LAUNCH_URL", "https://vendorA.com/launch_url")

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = ["vendorA"]
        WOPI_CLIENTS_CONFIGURATION = {}

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert str(excinfo.value) == (
        "Value 'WOPI_VENDORA_MIMETYPES' is required to be set as the environment"
        " variable 'WOPI_VENDORA_MIMETYPES'"
    )


def test_wopi_configuration_missing_launch_url(monkeypatch):
    """
    When a WOPI client is missing the launch url configuration, a ValueError should be
    raised.
    """
    monkeypatch.setenv(
        "WOPI_VENDORA_MIMETYPES", "application/vnd.oasis.opendocument.text"
    )

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = ["vendorA"]
        WOPI_CLIENTS_CONFIGURATION = {}

    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    assert str(excinfo.value) == (
        "Value 'WOPI_VENDORA_LAUNCH_URL' is required to be set as the environment"
        " variable 'WOPI_VENDORA_LAUNCH_URL'"
    )


def test_no_wopi_configuration():
    """Without WOPI clients, the configuration should be empty."""

    class TestSettings(Base):
        """Fake test settings."""

        WOPI_CLIENTS = []
        WOPI_CLIENTS_CONFIGURATION = {}

    TestSettings.post_setup()

    assert not TestSettings.WOPI_CLIENTS_CONFIGURATION
