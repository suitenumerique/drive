"""Tests for the configure_wopi celery task."""

from django.core.cache import cache

import pytest
import responses

from wopi.tasks.configure_wopi import (
    WOPI_CONFIGURATION_CACHE_KEY,
    configure_wopi_clients,
)


@responses.activate
def test_configure_wopi_clients(settings):
    """Test the configure_wopi celery task."""

    settings.WOPI_CLIENTS = ["vendorA"]
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "vendorA": {
            "discovery_url": "https://vendorA.com/hosting/discovery",
        }
    }

    # pylint: disable=line-too-long
    responses.add(
        responses.GET,
        "https://vendorA.com/hosting/discovery",
        body="""
<wopi-discovery>
    <net-zone name="external-http">
        <app favIconUrl="http://localhost:9980/browser/0968141f2c/images/x-office-document.svg" name="writer">
            <action default="true" ext="sxw" name="view" urlsrc="http://localhost:9980/browser/0968141f2c/cool.html?"/>
            <action default="true" ext="odt" name="edit" urlsrc="http://localhost:9980/browser/0968141f2c/cool.html?"/>
        </app>
        <app name="application/vnd.oasis.opendocument.text">
            <action default="true" ext="" name="edit" urlsrc="http://localhost:9980/browser/0968141f2c/cool.html?"/>
        </app>
    </net-zone>
</wopi-discovery>
""",
    )

    assert cache.get(WOPI_CONFIGURATION_CACHE_KEY) is None

    configure_wopi_clients()

    # pylint: disable=line-too-long
    assert cache.get(WOPI_CONFIGURATION_CACHE_KEY) == {
        "mimetypes": {
            "application/vnd.oasis.opendocument.text": {
                "url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            },
        },
        "extensions": {
            "odt": {
                "url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            },
        },
    }


def test_configure_wopi_clients_no_clients_configured(settings):
    """Test the configure_wopi celery task with excluded mimetypes."""

    settings.WOPI_CLIENTS = []
    settings.WOPI_CLIENTS_CONFIGURATION = {}

    assert cache.get(WOPI_CONFIGURATION_CACHE_KEY) is None

    configure_wopi_clients()

    assert cache.get(WOPI_CONFIGURATION_CACHE_KEY) is None


@responses.activate
def test_configure_wopi_clients_request_failing(settings):
    """Test the configure_wopi celery task with a failing request."""

    settings.WOPI_CLIENTS = ["vendorA"]
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "vendorA": {
            "discovery_url": "https://vendorA.com/hosting/discovery",
        }
    }

    responses.add(
        responses.GET,
        "https://vendorA.com/hosting/discovery",
        status=500,
    )

    with pytest.raises(
        RuntimeError,
        match="status code 500 return by discovery url for wopi client vendorA is invalid",
    ):
        configure_wopi_clients()
