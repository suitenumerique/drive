"""Fixtures for tests in the drive core application"""

from unittest import mock

import pytest
import responses

USER = "user"
TEAM = "team"
VIA = [USER, TEAM]


@pytest.fixture
def mock_user_teams():
    """Mock for the "teams" property on the User model."""
    with mock.patch(
        "core.models.User.teams", new_callable=mock.PropertyMock
    ) as mock_teams:
        yield mock_teams


@pytest.fixture
def resource_server_backend(settings):
    """
    A fixture to create a user token for testing.
    """
    assert (
        settings.OIDC_RS_BACKEND_CLASS
        == "lasuite.oidc_resource_server.backend.ResourceServerBackend"
    )

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
