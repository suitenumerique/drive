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
                "launch_url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            },
        },
        "extensions": {
            "odt": {
                "launch_url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            },
        },
        "vendorA": {
            "proof_keys": {},
        },
    }


@responses.activate
def test_configure_wopi_clients_with_proof_keys(settings):
    """Test the configure_wopi celery task with client using proof key."""

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
    <proof-key 
        oldvalue="BgIAAACkAABSU0ExAAgAAAEAAQD75uIhulOrvFWdgiI3BUqZWj3Zxlii/oCz4CQpH72jYZgbPkKpFC0D0zXznEvn8jgkekLjTD4Q3Dj5UoqN7atjGqhcCuLyiKqkjbklrOS/PS/nhKNJjMWgEUksRKu2vHXJmUhO1FECEgwHM7TOQtDnVJuMV0TK5MsjuhV7cU4uLe42gnzrrLbmpLM6UroNkwOTw723AwrzUSlNVecwMOEijfZj9hhvPzsTuMkIf48OfCQZk5VUJh4/D4lLlvqwFd8Lu48KXvEstWgRF+13pieinmEmQXSgBLzqMi//I9BbpPQQAl1AIy5o0HayDthDDYx5mis3sVEBwEs8dIQJgoTT" 
        oldmodulus="04SCCYR0PEvAAVGxNyuaeYwNQ9gOsnbQaC4jQF0CEPSkW9Aj/y8y6rwEoHRBJmGeoiemd+0XEWi1LPFeCo+7C98VsPqWS4kPPx4mVJWTGSR8Do9/CMm4Ezs/bxj2Y/aNIuEwMOdVTSlR8woDt73DkwOTDbpSOrOk5ras63yCNu4tLk5xexW6I8vkykRXjJtU59BCzrQzBwwSAlHUTkiZyXW8tqtELEkRoMWMSaOE5y89v+SsJbmNpKqI8uIKXKgaY6vtjYpS+TjcED5M40J6JDjy50uc8zXTAy0UqUI+G5hho70fKSTgs4D+oljG2T1amUoFNyKCnVW8q1O6IeLm+w=="
        oldexponent="AQAB"
        value="BgIAAACkAABSU0ExAAgAAAEAAQD75uIhulOrvFWdgiI3BUqZWj3Zxlii/oCz4CQpH72jYZgbPkKpFC0D0zXznEvn8jgkekLjTD4Q3Dj5UoqN7atjGqhcCuLyiKqkjbklrOS/PS/nhKNJjMWgEUksRKu2vHXJmUhO1FECEgwHM7TOQtDnVJuMV0TK5MsjuhV7cU4uLe42gnzrrLbmpLM6UroNkwOTw723AwrzUSlNVecwMOEijfZj9hhvPzsTuMkIf48OfCQZk5VUJh4/D4lLlvqwFd8Lu48KXvEstWgRF+13pieinmEmQXSgBLzqMi//I9BbpPQQAl1AIy5o0HayDthDDYx5mis3sVEBwEs8dIQJgoTT"
        modulus="04SCCYR0PEvAAVGxNyuaeYwNQ9gOsnbQaC4jQF0CEPSkW9Aj/y8y6rwEoHRBJmGeoiemd+0XEWi1LPFeCo+7C98VsPqWS4kPPx4mVJWTGSR8Do9/CMm4Ezs/bxj2Y/aNIuEwMOdVTSlR8woDt73DkwOTDbpSOrOk5ras63yCNu4tLk5xexW6I8vkykRXjJtU59BCzrQzBwwSAlHUTkiZyXW8tqtELEkRoMWMSaOE5y89v+SsJbmNpKqI8uIKXKgaY6vtjYpS+TjcED5M40J6JDjy50uc8zXTAy0UqUI+G5hho70fKSTgs4D+oljG2T1amUoFNyKCnVW8q1O6IeLm+w=="
        exponent="AQAB"/>
</wopi-discovery>
""",
    )

    assert cache.get(WOPI_CONFIGURATION_CACHE_KEY) is None

    configure_wopi_clients()

    # pylint: disable=line-too-long
    assert cache.get(WOPI_CONFIGURATION_CACHE_KEY) == {
        "mimetypes": {
            "application/vnd.oasis.opendocument.text": {
                "launch_url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            },
        },
        "extensions": {
            "odt": {
                "launch_url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            },
        },
        "vendorA": {
            "proof_keys": {
                "old_public_key": b"-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA04SCCYR0PEvAAVGxNyua\neYwNQ9gOsnbQaC4jQF0CEPSkW9Aj/y8y6rwEoHRBJmGeoiemd+0XEWi1LPFeCo+7\nC98VsPqWS4kPPx4mVJWTGSR8Do9/CMm4Ezs/bxj2Y/aNIuEwMOdVTSlR8woDt73D\nkwOTDbpSOrOk5ras63yCNu4tLk5xexW6I8vkykRXjJtU59BCzrQzBwwSAlHUTkiZ\nyXW8tqtELEkRoMWMSaOE5y89v+SsJbmNpKqI8uIKXKgaY6vtjYpS+TjcED5M40J6\nJDjy50uc8zXTAy0UqUI+G5hho70fKSTgs4D+oljG2T1amUoFNyKCnVW8q1O6IeLm\n+wIDAQAB\n-----END PUBLIC KEY-----\n",
                "public_key": b"-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA04SCCYR0PEvAAVGxNyua\neYwNQ9gOsnbQaC4jQF0CEPSkW9Aj/y8y6rwEoHRBJmGeoiemd+0XEWi1LPFeCo+7\nC98VsPqWS4kPPx4mVJWTGSR8Do9/CMm4Ezs/bxj2Y/aNIuEwMOdVTSlR8woDt73D\nkwOTDbpSOrOk5ras63yCNu4tLk5xexW6I8vkykRXjJtU59BCzrQzBwwSAlHUTkiZ\nyXW8tqtELEkRoMWMSaOE5y89v+SsJbmNpKqI8uIKXKgaY6vtjYpS+TjcED5M40J6\nJDjy50uc8zXTAy0UqUI+G5hho70fKSTgs4D+oljG2T1amUoFNyKCnVW8q1O6IeLm\n+wIDAQAB\n-----END PUBLIC KEY-----\n",
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
