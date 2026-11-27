"""Tests for the WOPI source-URL builder used by the conversion service."""

from unittest import mock

from django.core import signing

import pytest
from freezegun import freeze_time

from core import factories
from wopi.conversion import exceptions
from wopi.conversion.source_url import (
    build_source_url,
    build_system_source_url,
    read_system_source_token,
)


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


def test_build_system_source_url_signs_the_item_without_user(settings):
    """The system source URL carries a token signed for the item only."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example/"
    item = factories.ItemFactory.build()

    url = build_system_source_url(item)

    prefix = f"https://drive.example/api/v1.0/wopi/sources/{item.id}/?token="
    assert url.startswith(prefix)
    assert read_system_source_token(url.removeprefix(prefix)) == str(item.id)


def test_build_system_source_url_raises_when_base_url_is_missing(settings):
    """Raise when WOPI_SRC_BASE_URL is missing."""
    settings.WOPI_SRC_BASE_URL = None

    with pytest.raises(exceptions.ConversionMisconfigured, match="Missing WOPI_SRC_BASE_URL"):
        build_system_source_url(factories.ItemFactory.build())


def test_read_system_source_token_expires(settings):
    """System source tokens are only valid for WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example"
    settings.WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT = 90
    item = factories.ItemFactory.build()

    with freeze_time("2026-10-03 12:00:00"):
        token = build_system_source_url(item).split("token=")[1]
    with freeze_time("2026-10-03 12:01:29"):
        assert read_system_source_token(token) == str(item.id)
    with (
        freeze_time("2026-10-03 12:01:31"),
        pytest.raises(signing.SignatureExpired),
    ):
        read_system_source_token(token)


def test_read_system_source_token_rejects_other_signatures():
    """A value signed for another purpose is not a system source token."""
    with pytest.raises(signing.BadSignature):
        read_system_source_token(signing.dumps("some-id"))
