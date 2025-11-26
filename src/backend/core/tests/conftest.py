"""Fixtures for tests in the drive core application"""

import base64
from unittest import mock

from django.core.cache import cache

import pytest
import responses

from core import factories
from core.tests.utils.urls import reload_urls

USER = "user"
TEAM = "team"
VIA = [USER, TEAM]


@pytest.fixture(autouse=True)
def clear_cache():
    """Fixture to clear the cache after each test."""
    yield
    cache.clear()
    # Clear functools.cache for functions decorated with @functools.cache

    from core.entitlements import (  # pylint:disable=import-outside-toplevel # noqa: PLC0415
        get_entitlements_backend,
    )
    from core.storage import (  # pylint:disable=import-outside-toplevel # noqa: PLC0415
        get_storage_compute_backend,
    )

    get_entitlements_backend.cache_clear()
    get_storage_compute_backend.cache_clear()


@pytest.fixture
def mock_user_teams():
    """Mock for the "teams" property on the User model."""
    with mock.patch(
        "core.models.User.teams", new_callable=mock.PropertyMock
    ) as mock_teams:
        yield mock_teams


def resource_server_backend_setup(settings):
    """
    A fixture to create a user token for testing.
    """
    assert (
        settings.OIDC_RS_BACKEND_CLASS
        == "lasuite.oidc_resource_server.backend.ResourceServerBackend"
    )

    settings.OIDC_RESOURCE_SERVER_ENABLED = True
    settings.OIDC_RS_CLIENT_ID = "some_client_id"
    settings.OIDC_RS_CLIENT_SECRET = "some_client_secret"

    settings.OIDC_OP_URL = "https://oidc.example.com"
    settings.OIDC_VERIFY_SSL = False
    settings.OIDC_TIMEOUT = 5
    settings.OIDC_PROXY = None
    settings.OIDC_OP_JWKS_ENDPOINT = "https://oidc.example.com/jwks"
    settings.OIDC_OP_INTROSPECTION_ENDPOINT = "https://oidc.example.com/introspect"
    settings.OIDC_RS_SCOPES = ["openid", "groups"]
    settings.OIDC_RS_ALLOWED_AUDIENCES = ["some_service_provider"]


@pytest.fixture
def resource_server_backend_conf(settings):
    """
    A fixture to create a user token for testing.
    """
    resource_server_backend_setup(settings)
    reload_urls()


@pytest.fixture
def resource_server_backend(settings):
    """
    A fixture to create a user token for testing.
    Including a mocked introspection endpoint.
    """
    resource_server_backend_setup(settings)
    reload_urls()

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://oidc.example.com/introspect",
            json={
                "iss": "https://oidc.example.com",
                "aud": "some_client_id",  # settings.OIDC_RS_CLIENT_ID
                "sub": "very-specific-sub",
                "client_id": "some_service_provider",
                "scope": "openid groups",
                "active": True,
            },
        )

        yield rsps


@pytest.fixture
def user_specific_sub():
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


@pytest.fixture
def user_token():
    """
    A fixture to create a user token for testing.
    """
    return build_authorization_bearer("some_token")
