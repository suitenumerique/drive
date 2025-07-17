"""
Test SDK relay API endpoints.
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_api_sdk_relay_get_event_anonymous():
    """Anonymous users should be allowed to get an event."""
    client = APIClient()
    response = client.get("/api/v1.0/sdk-relay/events/123/")
    assert response.status_code == 200
    assert response.json() == {}


def test_api_sdk_relay_register_event():
    """Anonymous users should be allowed to register an event."""
    client = APIClient()

    response = client.get("/api/v1.0/sdk-relay/events/123/")
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
        {"token": "123", "event": {"type": "test"}},
        format="json",
    )
    assert response.status_code == 201

    response = client.get("/api/v1.0/sdk-relay/events/123/")
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
    response = client.get("/api/v1.0/sdk-relay/events/123/")
    assert response.status_code == 200
    assert response.json() == {}
