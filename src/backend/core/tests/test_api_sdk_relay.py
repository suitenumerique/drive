"""
Test SDK relay API endpoints.
"""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers

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
    assert response.json() == {}

    response = client.post("/api/v1.0/sdk-relay/events/", {"token": "123", "event": {"type": "test"}}, format="json")
    assert response.status_code == 201

    response = client.get("/api/v1.0/sdk-relay/events/123/")
    assert response.status_code == 200
    assert response.json() == {"type": "test"}

    # The event should be removed after it is retrieved
    response = client.get("/api/v1.0/sdk-relay/events/123/")
    assert response.status_code == 200
    assert response.json() == {}