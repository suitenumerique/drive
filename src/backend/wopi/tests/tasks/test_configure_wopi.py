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
            <action default="true" ext="odt" name="view" urlsrc="http://localhost:9980/browser/0968141f2c/cool.html?"/>
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
                "edit": {
                    "url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                    "client": "vendorA",
                },
            },
        },
        "extensions": {
            "odt": {
                "edit": {
                    "url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                    "client": "vendorA",
                },
                "view": {
                    "url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                    "client": "vendorA",
                },
            },
            "sxw": {
                "view": {
                    "url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                    "client": "vendorA",
                }
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


_LEGACY_DISCOVERY_BODY = """
<wopi-discovery>
    <net-zone name="external-http">
        <app name="writer">
            <action default="true" ext="doc" name="edit" urlsrc="http://example.com/edit?"/>
            <action default="true" ext="doc" name="view" urlsrc="http://example.com/view?"/>
            <action default="true" ext="doc" name="convert" urlsrc="http://example.com/convert?"/>
        </app>
        <app name="application/msword">
            <action default="true" ext="" name="edit" urlsrc="http://example.com/edit?"/>
            <action default="true" ext="" name="view" urlsrc="http://example.com/view?"/>
        </app>
    </net-zone>
</wopi-discovery>
"""


@responses.activate
def test_configure_wopi_clients_keeps_edit_without_force_convert(settings):
    """Without ForceConvertExtensions option, edit on .doc is kept (Collabora case)."""

    settings.WOPI_CLIENTS = ["collabora"]
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "collabora": {
            "discovery_url": "https://collabora.example.com/hosting/discovery",
            "options": {},
        }
    }

    responses.add(
        responses.GET,
        "https://collabora.example.com/hosting/discovery",
        body=_LEGACY_DISCOVERY_BODY,
    )

    configure_wopi_clients()

    config = cache.get(WOPI_CONFIGURATION_CACHE_KEY)
    assert "edit" in config["extensions"]["doc"]
    assert "edit" in config["mimetypes"]["application/msword"]


@responses.activate
def test_configure_wopi_clients_filters_edit_when_force_convert_set(settings):
    """With ForceConvertExtensions/ForceConvertMimetypes set (OnlyOffice case), edit is
    dropped for the listed legacy extensions/mimetypes; view and convert remain."""

    settings.WOPI_CLIENTS = ["onlyoffice"]
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "onlyoffice": {
            "discovery_url": "https://onlyoffice.example.com/hosting/discovery",
            "options": {
                "ForceConvertExtensions": ["doc"],
                "ForceConvertMimetypes": ["application/msword"],
            },
        }
    }

    responses.add(
        responses.GET,
        "https://onlyoffice.example.com/hosting/discovery",
        body=_LEGACY_DISCOVERY_BODY,
    )

    configure_wopi_clients()

    config = cache.get(WOPI_CONFIGURATION_CACHE_KEY)
    assert "edit" not in config["extensions"]["doc"]
    assert "view" in config["extensions"]["doc"]
    assert "convert" in config["extensions"]["doc"]
    assert "edit" not in config["mimetypes"]["application/msword"]
    assert "view" in config["mimetypes"]["application/msword"]


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
