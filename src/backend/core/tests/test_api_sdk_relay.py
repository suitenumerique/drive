"""
Test SDK relay API endpoints.
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_api_sdk_relay_get_event_anonymous():
    """Anonymous users should be allowed to get an event."""
    client = APIClient()
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert response.status_code == 200
    assert response.json() == {}


def test_api_sdk_relay_register_event():
    """Anonymous users should be allowed to register an event."""
    client = APIClient()

    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    assert (
        response["Access-Control-Allow-Methods"]
        == "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    assert (
        response["Access-Control-Allow-Headers"]
        == "Content-Type, Authorization, X-Requested-With"
    )
    assert response.json() == {}

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
    assert response["Access-Control-Allow-Origin"] == "*"
    assert (
        response["Access-Control-Allow-Methods"]
        == "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    assert (
        response["Access-Control-Allow-Headers"]
        == "Content-Type, Authorization, X-Requested-With"
    )
    assert response.json() == {"type": "test"}

    # The event should be removed after it is retrieved
    response = client.get(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/"
    )
    assert response.status_code == 200
    assert response.json() == {}


def test_api_sdk_relay_register_event_invalid_token():
    """Invalid token should return a 400 error."""
    client = APIClient()
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

def test_api_sdk_relay_preflight_request():
    """Preflight request should return a 200 status code."""
    client = APIClient()
    response = client.options(
        "/api/v1.0/sdk-relay/events/1Az6SO4CE7JAl9hE96dXl7145nghwZNP/",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    assert (
        response["Access-Control-Allow-Methods"]
        == "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    assert (
        response["Access-Control-Allow-Headers"]
        == "Content-Type, Authorization, X-Requested-With"
    )