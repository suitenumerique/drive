"""
Tests for the authentication of the external API through Menshen token exchange.
"""

import httpx2
import pytest
from rest_framework import exceptions
from rest_framework.test import APIClient, APIRequestFactory

from core import factories, models
from core.external_api.authentication import (
    MenshenAuthentication,
)
from core.tests.utils.menshen import (
    MENSHEN_EMAIL,
    MENSHEN_INTROSPECTION_URL,
    MENSHEN_SUB,
    MENSHEN_TOKEN,
    introspection_mock,
)

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


def build_request(token=MENSHEN_TOKEN, scheme="Bearer"):
    """Build a request carrying an Authorization header, or none at all."""
    if token is None:
        return APIRequestFactory().get("/")

    return APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"{scheme} {token}")


# Deferring to the next authentication backend


def test_menshen_authenticate_backend_disabled(settings, httpx2_mock):
    """No token should be introspected while the backend is disabled."""
    settings.MENSHEN_ENABLED = False

    # Nothing is registered: reaching Menshen would fail the test.
    assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_without_authorization_header(menshen_backend_conf, httpx2_mock):
    """A request carrying no token should defer to the next backend."""
    assert MenshenAuthentication().authenticate(build_request(token=None)) is None


def test_menshen_authenticate_other_authorization_scheme(menshen_backend_conf, httpx2_mock):
    """A token that is not a bearer token should defer to the next backend."""
    assert MenshenAuthentication().authenticate(build_request(scheme="Basic")) is None


def test_menshen_authenticate_inactive_token(menshen_backend_conf, httpx2_mock):
    """An expired, revoked or unknown token should defer to the next backend."""
    httpx2_mock.post(MENSHEN_INTROSPECTION_URL).respond(json={"active": False})

    assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_unreachable(menshen_backend_conf, httpx2_mock):
    """An unreachable Menshen should defer to the next backend."""
    httpx2_mock.post(MENSHEN_INTROSPECTION_URL).mock(
        side_effect=httpx2.ConnectError("Menshen is down")
    )

    assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_refuses_our_credentials(
    menshen_backend_conf, httpx2_mock
):
    """Menshen refusing Drive's client credentials should defer to the next backend."""
    httpx2_mock.post(MENSHEN_INTROSPECTION_URL).respond(401, json={})

    assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_not_json(menshen_backend_conf, httpx2_mock):
    """A response Drive cannot parse should defer to the next backend."""
    httpx2_mock.post(MENSHEN_INTROSPECTION_URL).respond(text="not json")

    assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_invalid_server_url(menshen_backend_conf, httpx2_mock):
    """A malformed Menshen server url should defer to the next backend, not crash."""
    menshen_backend_conf.MENSHEN_SERVER_URL = "https://menshen.example.com:port"

    assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_unknown_field(menshen_backend_conf, httpx2_mock):
    """A response carrying a field Drive's client ignores should defer, not crash."""
    introspection_mock(httpx2_mock, some_field_from_a_newer_menshen="unknown-field")

    assert MenshenAuthentication().authenticate(build_request()) is None


# Refusing the request


def test_menshen_authenticate_active_token_without_sub(menshen_backend_conf, httpx2_mock):
    """An active token that identifies no subject should be refused."""
    introspection_mock(httpx2_mock, sub=None)

    with pytest.raises(exceptions.AuthenticationFailed):
        MenshenAuthentication().authenticate(build_request())


def test_menshen_authenticate_inactive_user(menshen_backend_conf, httpx2_mock):
    """A disabled account should be refused."""
    factories.UserFactory(sub=MENSHEN_SUB, is_active=False)
    introspection_mock(httpx2_mock)

    with pytest.raises(exceptions.AuthenticationFailed):
        MenshenAuthentication().authenticate(build_request())


def test_menshen_authenticate_unknown_sub_without_user_creation(menshen_backend_conf, httpx2_mock):
    """No account should be provisioned while MENSHEN_CREATE_USER is off."""
    menshen_backend_conf.MENSHEN_CREATE_USER = False
    introspection_mock(httpx2_mock)

    with pytest.raises(exceptions.AuthenticationFailed):
        MenshenAuthentication().authenticate(build_request())

    assert not models.User.objects.filter(sub=MENSHEN_SUB).exists()


def test_menshen_authenticate_email_already_used(menshen_backend_conf, httpx2_mock):
    """A sub Drive does not know should not claim the email of an existing account."""
    factories.UserFactory(email=MENSHEN_EMAIL)
    introspection_mock(httpx2_mock)

    with pytest.raises(exceptions.AuthenticationFailed):
        MenshenAuthentication().authenticate(build_request())

    assert not models.User.objects.filter(sub=MENSHEN_SUB).exists()


def test_menshen_authenticate_email_already_used_in_another_case(menshen_backend_conf, httpx2_mock):
    """The email of an existing account should be matched case insensitively."""
    factories.UserFactory(email=MENSHEN_EMAIL.upper())
    introspection_mock(httpx2_mock)

    with pytest.raises(exceptions.AuthenticationFailed):
        MenshenAuthentication().authenticate(build_request())

    assert not models.User.objects.filter(sub=MENSHEN_SUB).exists()


def test_menshen_authenticate_duplicate_emails_allowed(menshen_backend_conf, httpx2_mock):
    """A deployment allowing duplicate emails should accept the new account."""
    menshen_backend_conf.OIDC_ALLOW_DUPLICATE_EMAILS = True
    factories.UserFactory(email=MENSHEN_EMAIL)
    introspection_mock(httpx2_mock)

    user, _payload = MenshenAuthentication().authenticate(build_request())

    assert user.sub == MENSHEN_SUB
    assert models.User.objects.filter(email__iexact=MENSHEN_EMAIL).count() == 2


# Authenticating the subject of the token


def test_menshen_authenticate_known_user(menshen_backend_conf, httpx2_mock):
    """An active token should authenticate the user matching its subject."""
    user = factories.UserFactory(sub=MENSHEN_SUB)
    introspection_mock(httpx2_mock)

    authenticated, payload = MenshenAuthentication().authenticate(build_request())

    assert authenticated == user
    assert payload["sub"] == MENSHEN_SUB
    assert models.User.objects.count() == 1


@pytest.mark.parametrize("scheme", ["bearer", "Bearer", "BEARER"])
def test_menshen_authenticate_scheme_is_case_insensitive(menshen_backend_conf, httpx2_mock, scheme):
    """The Authorization scheme should be matched case insensitively."""
    user = factories.UserFactory(sub=MENSHEN_SUB)
    introspection_mock(httpx2_mock)

    authenticated, _payload = MenshenAuthentication().authenticate(build_request(scheme=scheme))

    assert authenticated == user


def test_menshen_authenticate_creates_the_user(menshen_backend_conf, httpx2_mock):
    """A subject Drive has never seen should be provisioned from the token claims.

    Menshen forwards the sub and the email of the subject token:
    a provisioned account carries no name and no claims.
    """
    introspection_mock(httpx2_mock)

    user, _payload = MenshenAuthentication().authenticate(build_request())

    assert user.sub == MENSHEN_SUB
    assert user.email == MENSHEN_EMAIL
    assert user.has_usable_password() is False
    assert user.claims == {}


def test_menshen_authenticate_does_not_update_the_known_user(menshen_backend_conf, httpx2_mock):
    """An exchanged token should not rewrite the email of an existing account."""
    user = factories.UserFactory(sub=MENSHEN_SUB, email="other@example.com")
    introspection_mock(httpx2_mock)

    MenshenAuthentication().authenticate(build_request())

    user.refresh_from_db()
    assert user.email == "other@example.com"


@pytest.mark.parametrize(
    "scope,expected",
    [
        ("drive:item:list", ["drive:item:list"]),
        ("drive:item:list drive:item:retrieve", ["drive:item:list", "drive:item:retrieve"]),
        ("", []),
        (None, []),
    ],
)
def test_menshen_authenticate_exposes_the_scopes_as_a_list(
    menshen_backend_conf, httpx2_mock, scope, expected
):
    """The space separated scope should reach the permissions as a list."""
    factories.UserFactory(sub=MENSHEN_SUB)
    introspection_mock(httpx2_mock, scope=scope)

    _user, payload = MenshenAuthentication().authenticate(build_request())

    assert payload["scope"] == expected


def test_menshen_authenticate_header_answers_401():
    """Unauthenticated request gets a 401."""
    assert MenshenAuthentication().authenticate_header(build_request()) == "bearer"


# Alongside the resource server


def list_items_with_a_resource_server_token(user):
    """List items with a resource server token, for a user reading one of them."""
    # A file would still be pending upload, which the listing leaves out.
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED, type=models.ItemTypeChoices.FOLDER
    )
    factories.UserItemAccessFactory(item=item, user=user, role="reader")

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer some_resource_server_token")

    return item, client.get("/external_api/v1.0/items/")


def test_api_items_list_resource_server_token_unknown_to_menshen(
    menshen_backend_conf, resource_server_backend, httpx2_mock, user_specific_sub
):
    """Menshen not knowing a resource server token should defer to the resource server.

    Fixture order matters, as menshen_backend_conf deactivates resource server
    authentication.
    """
    httpx2_mock.post(MENSHEN_INTROSPECTION_URL).respond(json={"active": False})

    item, response = list_items_with_a_resource_server_token(user_specific_sub)

    assert response.status_code == 200
    assert str(item.id) in [result["id"] for result in response.json()["results"]]
