"""
Test Entitlements API endpoints.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories
from core.entitlements import get_entitlements_backend

pytestmark = pytest.mark.django_db


def test_api_entitlements_get_entitlements_anonymous():
    """Anonymous users should not be allowed to get entitlements."""
    client = APIClient()
    response = client.get("/api/v1.0/entitlements/")
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


def test_api_entitlements_get_entitlements_authenticated():
    """Authenticated users should be allowed to get entitlements."""
    client = APIClient()
    user = factories.UserFactory()
    client.force_authenticate(user)
    response = client.get("/api/v1.0/entitlements/")
    assert response.status_code == 200
    assert response.json() == {
        "can_access": {
            "result": True,
        },
        "can_upload": {
            "result": True,
        },
    }


def test_api_entitlements_get_entitlements_entitlements_backend_returns_falsy():
    """Authenticated users should be allowed to get entitlements with a custom message."""

    real_backend = get_entitlements_backend()
    real_backend.can_access = mock.Mock(
        return_value={"result": False, "message": "You do not have access to the app"}
    )

    with mock.patch(
        "core.api.viewsets.get_entitlements_backend", return_value=real_backend
    ):
        client = APIClient()
        user = factories.UserFactory()
        client.force_authenticate(user)
        response = client.get("/api/v1.0/entitlements/")
        assert response.status_code == 200
        assert response.json() == {
            "can_access": {
                "result": False,
                "message": "You do not have access to the app",
            },
            "can_upload": {
                "result": True,
            },
        }
