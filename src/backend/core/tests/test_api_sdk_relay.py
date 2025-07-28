"""
Test SDK relay API endpoints.
"""

import pytest
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


def test_api_sdk_relay_get_event_anonymous():
    """Anonymous users should be allowed to get an event."""
    client = APIClient()
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert response.status_code == 200
    assert response.json() == {}


def test_api_sdk_relay_register_event_anonymous():
    """Anonymous users should not be allowed to register an event."""
    client = APIClient()
    response = client.post(
        "/api/v1.0/sdk-relay/events/",
        {"token": "1Az6SO4CE7JAl9hE96dXl7145nghwZNP", "event": {"type": "test"}},
        format="json",
    )
    assert response.status_code == 401


def test_api_sdk_relay_register_event():
    """Anonymous users should be allowed to register an event."""
    client = APIClient()

    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert "Access-Control-Allow-Origin" not in response
    assert response.json() == {}

    user = factories.UserFactory()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1.0/sdk-relay/events/",
        {"token": "1Az6SO4CE7JAl9hE96dXl7145nghwZNP", "event": {"type": "test"}},
        format="json",
    )
    assert response.status_code == 201

    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response
    assert response.json() == {"type": "test"}

    # The event should be removed after it is retrieved
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert response.status_code == 200
    assert response.json() == {}


def test_api_sdk_relay_register_event_invalid_token():
    """Invalid token should return a 400 error."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1.0/sdk-relay/events/",
        {"token": "123", "event": {"type": "test"}},
        format="json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "token",
                "code": "invalid",
                "detail": "This value does not match the required pattern.",
            }
        ],
        "type": "validation_error",
    }


def test_api_sdk_relay_register_event_too_long():
    """Event data exceeding maximum length should return a 400 error."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)

    # Create a large event payload that exceeds the max length
    large_event = {
        "type": "test",
        "data": {
            "items": [
                {
                    "id": str(i),
                    "title": "x" * 900,  # Long title to help exceed limit
                    "size": 1000,
                    "url": "http://example.com/" + ("y" * 100),
                }
                for i in range(200)  # Many items to exceed limit
            ]
        },
    }

    response = client.post(
        "/api/v1.0/sdk-relay/events/",
        {"token": "1Az6SO4CE7JAl9hE96dXl7145nghwZNP", "event": large_event},
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "event",
                "code": "invalid",
                "detail": "Event data exceeds maximum length of 100000 characters.",
            }
        ],
        "type": "validation_error",
    }


def test_api_sdk_relay_preflight_request(settings):
    """Preflight request should return a 200 status code."""
    settings.SDK_CORS_ALLOWED_ORIGINS = ["http://allowed-domain.com"]
    client = APIClient()
    response = client.options(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/",
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response

    response = client.options(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/",
        HTTP_ORIGIN="http://allowed-domain.com",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "http://allowed-domain.com"
    assert response["Access-Control-Allow-Methods"] == "GET, OPTIONS"


def test_api_sdk_relay_allowed_origins(settings):
    """Test that SDK relay requests are only allowed from configured origins."""
    settings.SDK_CORS_ALLOWED_ORIGINS = ["http://allowed-domain.com"]
    client = APIClient()

    # Test request from allowed origin
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/",
        HTTP_ORIGIN="http://allowed-domain.com",
    )
    assert response["Access-Control-Allow-Origin"] == "http://allowed-domain.com"
    assert response["Access-Control-Allow-Methods"] == "GET, OPTIONS"

    # Test request from disallowed origin
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/",
        HTTP_ORIGIN="http://disallowed-domain.com",
    )
    assert "Access-Control-Allow-Origin" not in response
    assert "Access-Control-Allow-Methods" not in response

    # Test request with no origin header
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert "Access-Control-Allow-Origin" not in response
    assert "Access-Control-Allow-Methods" not in response
