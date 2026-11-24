"""
Tests for the external API url configuration.

Every resource accepts both a resource server token and a token exchanged through
Menshen: enabling either one registers the resources EXTERNAL_API enables.
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


def test_api_external_not_registered_by_default():
    """If neither backend being enabled, the external API should not be accessible."""
    reload_urls()

    assert APIClient().get("/external_api/v1.0/items/").status_code == 404


def test_api_external_items_registered_with_menshen_only(menshen_backend_conf):
    """Enabling Menshen alone should expose items route."""
    assert APIClient().get("/external_api/v1.0/items/").status_code == 401


def test_api_external_users_registered_with_menshen_only(menshen_backend_conf):
    """Enabling Menshen alone should expose the users route."""
    assert menshen_backend_conf.EXTERNAL_API["users"]["enabled"] is True

    assert APIClient().get("/external_api/v1.0/users/me/").status_code == 401


def test_api_external_users_disabled_with_menshen_only(menshen_backend_conf):
    """Enabling Menshen should not register the users route EXTERNAL_API disables."""
    menshen_backend_conf.EXTERNAL_API = {"users": {"enabled": False, "actions": ["get_me"]}}
    reload_urls()

    assert APIClient().get("/external_api/v1.0/users/me/").status_code == 404


@pytest.mark.parametrize(
    "resource,path", [("item_access", "accesses"), ("item_invitation", "invitations")]
)
def test_api_external_nested_routes_registered_with_menshen_only(
    menshen_backend_conf, resource, path
):
    """Enabling Menshen alone should expose the nested routes EXTERNAL_API enables."""
    menshen_backend_conf.EXTERNAL_API = {resource: {"enabled": True, "actions": ["list"]}}
    reload_urls()

    response = APIClient().get(f"/external_api/v1.0/items/{uuid4()!s}/{path}/")

    assert response.status_code == 401


@pytest.mark.parametrize("path", ["accesses", "invitations"])
def test_api_external_nested_routes_disabled_by_default_with_menshen_only(
    menshen_backend_conf, path
):
    """Enabling Menshen should not register the nested routes, disabled by default."""
    response = APIClient().get(f"/external_api/v1.0/items/{uuid4()!s}/{path}/")

    assert response.status_code == 404


def test_api_external_users_registered_with_the_resource_server(resource_server_backend_conf):
    """Enabling the resource server should keep registering the other resources."""
    assert APIClient().get("/external_api/v1.0/users/me/").status_code == 401


def test_api_external_users_registered_with_menshen_and_resource_server(
    menshen_backend_conf, resource_server_backend_conf
):
    """Enabling Menshen on top of the resource server should keep the users route.

    Fixture order matters: menshen_backend_conf turns the resource server off,
    resource_server_backend_conf turns it back on.
    """
    assert APIClient().get("/external_api/v1.0/users/me/").status_code == 401
