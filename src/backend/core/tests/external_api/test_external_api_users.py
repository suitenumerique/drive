"""
Tests for the Resource Server API for users.

Not testing external API endpoints that are already tested in the /api
because the resource server viewsets inherit from the api viewsets.

"""

import pytest
from rest_framework.test import APIClient

from core import factories
from core.tests.external_api.utils import reload_urls

pytestmark = pytest.mark.django_db


def test_api_users_me_anonymous_public_standalone():
    """
    Anonymous users should not be allowed to retrieve their own user information from external
    API if resource server is not enabled.
    """
    reload_urls()
    response = APIClient().get(f"/external_api/v1.0/users/me/")

    assert response.status_code == 404


def test_api_users_me_connected_not_resource_server():
    """
    Connected users should not be allowed to retrieve their own user information from external
    API if resource server is not enabled.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get(f"/external_api/v1.0/users/me/")

    assert response.status_code == 404


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

    response = client.get(f"/external_api/v1.0/users/me/")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_specific_sub.id)
    assert data["email"] == user_specific_sub.email


def test_api_users_me_connected_resource_server_with_invalid_token(
    user_token, resource_server_backend
):
    """
    Connected users should not be allowed to retrieve their own user information from external API
    if resource server is enabled with an invalid token.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get(f"/external_api/v1.0/users/me/")

    assert response.status_code == 401


def test_api_users_list_resource_server_(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should notbe allowed to list users from a resource server.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get(f"/external_api/v1.0/users/")

    assert response.status_code == 403
