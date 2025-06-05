"""Tests for the Resource Server API for items."""

from datetime import datetime, timedelta, timezone

from django.test import override_settings

import jwt
import pytest
from rest_framework.test import APIClient

from core import factories
from core.models import Item, User

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


@pytest.fixture(name="user_specific_sub")
def fixture_user_specific_sub():
    """
    A fixture to create a user token for testing.
    """
    user = factories.UserFactory(sub="very-specific-sub")
    yield user


@pytest.fixture(name="jwt_token")
def fixture_jwt_token(settings, user_specific_sub):
    """
    A fixture to create a JWT token for testing.
    """
    settings.JWT_SECRET_KEY = "test-secret"
    settings.JWT_ALGORITHM = "HS256"
    expired_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    yield jwt.encode(
        {
            "sub": user_specific_sub.sub,
            "email": user_specific_sub.email,
            "exp": expired_at.timestamp(),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture(name="invalid_jwt_token")
def fixture_invalid_jwt_token(settings):
    """
    A fixture to create an invalid JWT token for testing.
    """
    settings.JWT_SECRET_KEY = "test-secret"
    settings.JWT_ALGORITHM = "HS256"
    yield jwt.encode(
        {"sub": "invalid-sub", "email": "invalid-email"},
        "invalid-secret",
        algorithm=settings.JWT_ALGORITHM,
    )


def test_api_items_retrieve_anonymous_public_standalone():
    """Anonymous users should not be allowed to retrieve an item."""
    item = factories.ItemFactory(link_reach="public")

    response = APIClient().get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


def test_api_items_retrieve_connected(jwt_token):
    """Connected users should be allowed to retrieve an item."""
    client = APIClient()
    item = factories.ItemFactory(link_reach="public")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 200


def test_api_items_retrieve_connected_with_invalid_token(invalid_jwt_token):
    """User with an invalid sub should not be allowed to retrieve an item."""
    client = APIClient()
    item = factories.ItemFactory(link_reach="public")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/",
        HTTP_AUTHORIZATION=f"Bearer {invalid_jwt_token}",
    )

    assert response.status_code == 403


def test_api_items_retrieve_connected_with_wrong_abilities(
    jwt_token, user_specific_sub
):
    """User with wrong abilities should not be allowed to retrieve an item."""

    client = APIClient()
    item = factories.ItemFactory(link_reach="restricted")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 403


def test_api_items_retrieve_fetch_api_using_access_token(jwt_token, user_specific_sub):
    """
    User with an access token should not be allowed to retrieve an item from
    the api endpoint.
    """

    client = APIClient()
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/", HTTP_AUTHORIZATION=f"Bearer {jwt_token}"
    )

    assert response.status_code == 403


def test_api_items_accesses_retrieve_anonymous_public_standalone():
    """Anonymous users should not be allowed to retrieve an item."""
    item = factories.ItemFactory(link_reach="public")

    response = APIClient().get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 403


def test_api_items_accesses_retrieve_connected():
    """
    Connected users should not be allowed to retrieve an item if they don't have a jwt token.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="public")

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 403


def test_api_items_accesses_retrieve_connected_with_good_abilities(jwt_token):
    """Connected users should be allowed to retrieve an item if they have a jwt token."""
    client = APIClient()
    item = factories.ItemFactory(link_reach="public")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 200


def test_api_items_accesses_retrieve_connected_with_invalid_token(invalid_jwt_token):
    """User with an invalid sub should not be allowed to retrieve an item."""
    client = APIClient()
    item = factories.ItemFactory(link_reach="public")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        HTTP_AUTHORIZATION=f"Bearer {invalid_jwt_token}",
    )

    assert response.status_code == 403


def test_api_items_accesses_retrieve_connected_with_wrong_abilities(jwt_token):
    """User with wrong abilities should not be allowed to retrieve an item accesses."""

    client = APIClient()
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory.create_batch(3, item=item)

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_api_items_accesses_retrieve_fetch_api_using_jwt_token(
    jwt_token, user_specific_sub
):
    """
    User with a jwt token should not be allowed to retrieve an item from
    the api endpoint.
    """

    client = APIClient()
    item = factories.ItemFactory(link_reach="restricted")
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 403


@override_settings(JWT_CREATE_USER=False)
def test_api_items_accesses_retrieve_new_user_and_create_user_disabled(
    jwt_token, user_specific_sub
):
    """New users should not be allowed to retrieve an item if JWT_CREATE_USER=False."""

    # Delete the user and its workspace
    Item.objects.filter(creator__sub=user_specific_sub.sub).delete()
    user_specific_sub.delete()

    client = APIClient()
    item = factories.ItemFactory(link_reach="public")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 403
    assert not User.objects.filter(
        sub=user_specific_sub.sub, email=user_specific_sub.email
    ).exists()


@override_settings(JWT_CREATE_USER=True)
def test_api_items_accesses_retrieve_new_user_and_create_user_enabled(
    jwt_token, user_specific_sub
):
    """New users should be allowed to retrieve an item if JWT_CREATE_USER=True."""

    # Delete the user and its workspace
    Item.objects.filter(creator__sub=user_specific_sub.sub).delete()
    user_specific_sub.delete()

    client = APIClient()
    item = factories.ItemFactory(link_reach="public")

    response = client.get(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
    )

    assert response.status_code == 200

    # User should have been created again from the JWT token only.
    assert User.objects.filter(
        sub=user_specific_sub.sub, email=user_specific_sub.email
    ).exists()
