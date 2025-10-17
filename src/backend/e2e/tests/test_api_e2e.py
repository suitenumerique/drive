"""
Test e2e API endpoints.
"""

from django.test.utils import override_settings

import pytest
from rest_framework.test import APIClient

from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db


def test_api_e2e_user_auth_no_urls():
    """E2E URLs not enabled should 404."""
    client = APIClient()

    response = client.post("/api/v1.0/e2e/user-auth/", {"email": "test@example.com"})
    assert response.status_code == 404


@override_settings(LOAD_E2E_URLS=True)
def test_api_e2e_user_auth_anonymous():
    """Anonymous users should be allowed to create and login a user."""
    reload_urls()
    client = APIClient()

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 401

    response = client.post("/api/v1.0/e2e/user-auth/", {"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == {"email": "test@example.com"}

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@override_settings(LOAD_E2E_URLS=True)
def test_api_e2e_user_auth_authenticated():
    """Authenticated users should be allowed to create and login a new user."""
    reload_urls()
    client = APIClient()

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 401

    response = client.post("/api/v1.0/e2e/user-auth/", {"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == {"email": "test@example.com"}

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

    response = client.post("/api/v1.0/e2e/user-auth/", {"email": "test2@example.com"})
    assert response.status_code == 200
    assert response.json() == {"email": "test2@example.com"}

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 200
    assert response.json()["email"] == "test2@example.com"


@override_settings(LOAD_E2E_URLS=True)
def test_api_e2e_user_auth_email_required():
    """Email is required."""
    reload_urls()
    client = APIClient()

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 401

    response = client.post("/api/v1.0/e2e/user-auth/", {})
    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {"code": "required", "detail": "This field is required.", "attr": "email"}
        ],
    }
