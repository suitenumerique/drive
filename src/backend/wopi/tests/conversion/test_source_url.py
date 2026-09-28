"""Tests for the WOPI source-URL builder used by the conversion service."""

from unittest import mock

import pytest

from core import factories
from wopi.conversion import exceptions
from wopi.conversion.source_url import build_source_url


@pytest.fixture
def _access_service():
    """Mock the AccessUserItemService used by build_source_url."""
    service = mock.Mock()
    service.return_value.insert_new_access.return_value = ("tok-abc", 1_700_000_000_000)
    with mock.patch("wopi.conversion.source_url.AccessUserItemService", service):
        yield service


def test_build_source_url_uses_configured_wopi_base_url(settings, _access_service):
    """Start the built URL with WOPI_SRC_BASE_URL and embed the access token."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example"
    item = factories.ItemFactory.build()
    user = factories.UserFactory.build()

    url = build_source_url(item, user)

    assert url == (
        f"https://drive.example/api/v1.0/wopi/files/{item.id}/contents/?access_token=tok-abc"
    )


def test_build_source_url_strips_trailing_slash_on_base_url(settings, _access_service):
    """Strip a trailing slash on the base URL to avoid a double slash."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example/"
    item = factories.ItemFactory.build()
    user = factories.UserFactory.build()

    url = build_source_url(item, user)

    assert "//api" not in url


def test_build_source_url_raises_when_base_url_is_missing(settings, _access_service):
    """Raise when WOPI_SRC_BASE_URL is missing."""
    settings.WOPI_SRC_BASE_URL = None
    item = factories.ItemFactory.build()
    user = factories.UserFactory.build()

    with pytest.raises(exceptions.ConversionMisconfigured, match="Missing WOPI_SRC_BASE_URL"):
        build_source_url(item, user)


def test_build_source_url_delegates_to_access_user_item_service(settings, _access_service):
    """Issue a short-lived WOPI access token via the existing service."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example"
    settings.WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT = 90
    item = factories.ItemFactory.build()
    user = factories.UserFactory.build()

    build_source_url(item, user)

    _access_service.return_value.insert_new_access.assert_called_once_with(item, user, ttl=90)
