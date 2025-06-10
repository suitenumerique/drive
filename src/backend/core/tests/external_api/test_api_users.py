"""Test the external API users endpoints."""

import base64
from datetime import datetime, timedelta, timezone

import jwt
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


def test_api_user_resource_server_retrieve_anonymous():
    """Anonymous users should not be allowed to access the user endpoint."""
    factories.UserFactory()
    client = APIClient()
    response = client.get("/external_api/v1.0/users/")
    assert response.status_code == 403


def test_api_user_resource_server_retrieve_connected_jwt(jwt_token):
    """Connected users should be allowed to access the user endpoint."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_token}")
    response = client.get("/external_api/v1.0/users/")
    assert response.status_code == 200


def test_api_user_resource_server_retrieve_connected_access_token(
    user_token, resource_server_backend, user_specific_sub
):
    """Connected users should be allowed to access the user endpoint."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    response = client.get("/external_api/v1.0/users/")
    assert response.status_code == 200


def test_api_user_resource_server_retrieve_connected_access_token_invalid(
    user_token, resource_server_backend
):
    """Connected users should be allowed to access the user endpoint."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    response = client.get("/external_api/v1.0/users/")
    assert response.status_code == 403


def test_test_api_user_resource_server_retrieve_connected_invalid_jwt(
    invalid_jwt_token,
):
    """Connected users should be allowed to access the user endpoint."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {invalid_jwt_token}")
    response = client.get("/external_api/v1.0/users/")
    assert response.status_code == 403
