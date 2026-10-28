"""
Tests for the external API url configuration.

Items accept both a resource server token and a token exchanged through Menshen. The
other resources carry no Menshen authentication, so enabling Menshen alone must not
register them.
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


def test_api_external_users_not_registered_with_menshen_only(menshen_backend_conf):
    """Users carry no Menshen authentication, the route should stay unregistered."""
    assert menshen_backend_conf.EXTERNAL_API["users"]["enabled"] is True

    assert APIClient().get("/external_api/v1.0/users/me/").status_code == 404


@pytest.mark.parametrize("resource", ["accesses", "invitations"])
def test_api_external_nested_routes_not_registered_with_menshen_only(
    menshen_backend_conf, resource
):
    """The nested item resources should stay unregistered."""
    response = APIClient().get(f"/external_api/v1.0/items/{uuid4()!s}/{resource}/")

    assert response.status_code == 404


def test_api_external_users_registered_with_the_resource_server(resource_server_backend_conf):
    """Enabling the resource server should keep registering the other resources."""
    assert APIClient().get("/external_api/v1.0/users/me/").status_code == 401
