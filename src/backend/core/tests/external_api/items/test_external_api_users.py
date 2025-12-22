"""
Tests for the Resource Server API for users.

Not testing external API endpoints that are already tested in the /api
because the resource server viewsets inherit from the api viewsets.

"""

from django.test import override_settings

import pytest
from rest_framework.test import APIClient

from core import factories
from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


def test_api_users_list_connected_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to list users if resource server is not enabled.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get("/external_api/v1.0/users/")
    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "users": {
            "enabled": True,
            "actions": ["list"],
        }
    }
)
def test_api_users_list_connected_resource_server(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to list users if resource server is not enabled.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    factories.UserFactory(email="john.doe@example.com")

    response = client.get("/external_api/v1.0/users/?q=john.")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "john.doe@example.com"


@override_settings(
    EXTERNAL_API={
        "users": {
            "enabled": True,
            "actions": [],
        }
    }
)
def test_api_users_me_connected_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to retrieve their own user information if
    resource server is not enabled.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get("/external_api/v1.0/users/me/")
    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "users": {
            "enabled": True,
            "actions": ["get_me"],
        }
    }
)
def test_api_users_me_connected_resource_server(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to retrieve their own user information from external API
    if resource server is enabled.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get("/external_api/v1.0/users/me/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_specific_sub.id)
    assert data["email"] == user_specific_sub.email
