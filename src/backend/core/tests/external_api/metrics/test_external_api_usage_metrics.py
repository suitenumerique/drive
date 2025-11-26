"""
Tests for the usage metrics external API.
"""

from django.test import override_settings

import pytest
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from core import factories
from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


@pytest.fixture(name="api_key")
def fixture_api_key():
    """
    Create a API key for the test.
    The key is only available once at creation time, the one used
    in the requests, where key can be seen as the id of the API key.
    """
    _, key = APIKey.objects.create_key(name="my-remote-service")
    return key


@override_settings(METRICS_ENABLED=False)
def test_usage_metrics_disabled():
    """
    Usage metrics should be disabled if the METRICS_ENABLED setting is False.
    """
    reload_urls()
    response = APIClient().get("/external_api/v1.0/metrics/usage/")

    assert response.status_code == 404


@override_settings(METRICS_ENABLED=True)
def test_usage_metrics_no_keys():
    """
    Users should not be allowed to retrieve usage metrics without a valid API key.
    """
    reload_urls()
    response = APIClient().get("/external_api/v1.0/metrics/usage/")

    assert response.status_code == 401
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
    }


@override_settings(METRICS_ENABLED=True)
def test_usage_metrics_with_valid_key(api_key):
    """
    API keys should be allowed to retrieve usage metrics.
    """
    reload_urls()
    response = APIClient().get(
        "/external_api/v1.0/metrics/usage/", HTTP_AUTHORIZATION=f"Api-Key {api_key}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


@override_settings(METRICS_ENABLED=True)
def test_usage_metrics_list(api_key):
    """
    API keys should be allowed to list usage metrics for multiple accounts.
    """
    client = APIClient()
    user1 = factories.UserFactory()
    user2 = factories.UserFactory()

    factories.ItemFactory(creator=user1, size=100)

    response = client.get(
        "/external_api/v1.0/metrics/usage/", HTTP_AUTHORIZATION=f"Api-Key {api_key}"
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "account": {
                    "type": "user",
                    "id": str(user1.id),
                    "email": user1.email,
                },
                "metrics": {
                    "storage_used": 100,
                },
            },
            {
                "account": {
                    "type": "user",
                    "id": str(user2.id),
                    "email": user2.email,
                },
                "metrics": {
                    "storage_used": 0,
                },
            },
        ],
    }


@override_settings(METRICS_ENABLED=True)
def test_usage_metrics_list_filter_by_account_id(api_key):
    """
    API keys should be allowed to list usage metrics for a specific account.
    """
    client = APIClient()
    user1 = factories.UserFactory()
    factories.UserFactory()

    factories.ItemFactory(creator=user1, size=100)

    response = client.get(
        f"/external_api/v1.0/metrics/usage/?account_id={user1.id}",
        HTTP_AUTHORIZATION=f"Api-Key {api_key}",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "account": {
                    "type": "user",
                    "id": str(user1.id),
                    "email": user1.email,
                },
                "metrics": {
                    "storage_used": 100,
                },
            },
        ],
    }


@override_settings(METRICS_ENABLED=True, METRICS_USER_CLAIMS_EXPOSED=["iss", "aud"])
def test_usage_metrics_exposed_claims(api_key):
    """
    API keys should be allowed to list usage metrics for a specific account.
    """
    client = APIClient()
    user1 = factories.UserFactory(
        claims={"iss": "https://example.com", "aud": "https://example.com"}
    )
    user2 = factories.UserFactory(
        claims={"iss": "https://example2.com", "aud": "https://example2.com"}
    )

    factories.ItemFactory(creator=user1, size=100)

    response = client.get(
        "/external_api/v1.0/metrics/usage/", HTTP_AUTHORIZATION=f"Api-Key {api_key}"
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "account": {
                    "type": "user",
                    "id": str(user1.id),
                    "email": user1.email,
                },
                "iss": "https://example.com",
                "aud": "https://example.com",
                "metrics": {
                    "storage_used": 100,
                },
            },
            {
                "account": {
                    "type": "user",
                    "id": str(user2.id),
                    "email": user2.email,
                },
                "iss": "https://example2.com",
                "aud": "https://example2.com",
                "metrics": {
                    "storage_used": 0,
                },
            },
        ],
    }
