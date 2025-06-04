"""Tests for the Resource Server API for items."""

import base64

import pytest
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


@pytest.fixture(name="user_specific_sub")
def fixture_user_specific_sub():
    """
    A fixture to create a user token for testing.
    """
    user = factories.UserFactory(sub="very-specific-sub")

    yield user


def build_authorization_bearer(token):
    """
    Build an Authorization Bearer header value from a token.

    This can be used like this:
    client.post(
        ...
        HTTP_AUTHORIZATION=f"Bearer {build_authorization_bearer('some_token')}",
    )
    """
    return base64.b64encode(token.encode("utf-8")).decode("utf-8")


@pytest.fixture(name="user_token")
def fixture_user_token():
    """
    A fixture to create a user token for testing.
    """
    return build_authorization_bearer("some_token")


def test_api_items_retrieve_anonymous_public_standalone():
    """Anonymous users should not be allowed to retrieve an item."""
    item = factories.ItemFactory(link_reach="public")

    response = APIClient().get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


def test_api_items_retrieve_connected_not_resource_server():
    """
    Connected users should not be allowed to retrieve an item if they are not a resource server.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


def test_api_items_retrieve_connected_resource_server(
    user_token, resource_server_backend, user_specific_sub
):
    """Connected users should be allowed to retrieve an item if they are a resource server."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200


def test_api_items_retrieve_connected_resource_server_with_invalid_token(
    user_token, resource_server_backend
):
    """User with an invalid sub should not be allowed to retrieve an item."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


def test_api_items_retrieve_connected_resource_server_with_wrong_abilities(
    user_token, user_specific_sub, resource_server_backend
):
    """User with wrong abilities should not be allowed to retrieve an item."""

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200


def test_api_items_retrieve_fetch_api_using_access_token(user_token, user_specific_sub):
    """
    User with an access token should not be allowed to retrieve an item from
    the api endpoint.
    """

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


def test_api_items_accesses_retrieve_anonymous_public_standalone():
    """Anonymous users should not be allowed to retrieve an item."""
    item = factories.ItemFactory(link_reach="public")

    response = APIClient().get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 403


def test_api_items_accesses_retrieve_connected_not_resource_server():
    """
    Connected users should not be allowed to retrieve an item if they are not a resource server.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 403


def test_api_items_accesses_retrieve_connected_resource_server(
    user_token, resource_server_backend, user_specific_sub
):
    """Connected users should be allowed to retrieve an item if they are a resource server."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200


def test_api_items_accesses_retrieve_connected_resource_server_with_invalid_token(
    user_token, resource_server_backend
):
    """User with an invalid sub should not be allowed to retrieve an item."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 403


def test_api_items_accesses_retrieve_connected_resource_server_with_wrong_abilities(
    user_token, user_specific_sub, resource_server_backend
):
    """User with wrong abilities should not be allowed to retrieve an item."""

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200


def test_api_items_accesses_retrieve_fetch_api_using_access_token(
    user_token, user_specific_sub
):
    """
    User with an access token should not be allowed to retrieve an item from
    the api endpoint.
    """

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 403
