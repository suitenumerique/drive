"""
Tests for the authentication of the external API through Menshen token exchange.
"""


import pytest
import requests
import responses
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from core import factories, models
from core.external_api.authentication import (
    MenshenAuthentication,
)
from core.tests.utils.menshen import (
    MENSHEN_EMAIL,
    MENSHEN_INTROSPECTION_URL,
    MENSHEN_SUB,
    MENSHEN_TOKEN,
    menshen_introspection_response,
)

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


def build_request(token=MENSHEN_TOKEN, scheme="Bearer"):
    """Build a request carrying an Authorization header, or none at all."""
    if token is None:
        return APIRequestFactory().get("/")

    return APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"{scheme} {token}")


def introspection_mock(rsps, **overrides):
    """Register an active introspection response on a mocked Menshen."""
    return rsps.add(
        responses.POST,
        MENSHEN_INTROSPECTION_URL,
        json=menshen_introspection_response(**overrides),
    )


# Deferring to the next authentication backend


def test_menshen_authenticate_backend_disabled(settings):
    """No token should be introspected while the backend is disabled."""
    settings.MENSHEN_ENABLED = False

    # Nothing is registered: reaching the network would raise a ConnectionError.
    with responses.RequestsMock():
        assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_without_authorization_header(menshen_backend_conf):
    """A request carrying no token should defer to the next backend."""
    with responses.RequestsMock():
        assert MenshenAuthentication().authenticate(build_request(token=None)) is None


def test_menshen_authenticate_other_authorization_scheme(menshen_backend_conf):
    """A token that is not a bearer token should defer to the next backend."""
    with responses.RequestsMock():
        assert MenshenAuthentication().authenticate(build_request(scheme="Basic")) is None


def test_menshen_authenticate_inactive_token(menshen_backend_conf):
    """An expired, revoked or unknown token should defer to the next backend."""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, MENSHEN_INTROSPECTION_URL, json={"active": False})

        assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_unreachable(menshen_backend_conf):
    """An unreachable Menshen should defer to the next backend."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            MENSHEN_INTROSPECTION_URL,
            body=requests.ConnectionError("Menshen is down"),
        )

        assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_refuses_our_credentials(menshen_backend_conf):
    """Menshen refusing Drive's client credentials should defer to the next backend."""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, MENSHEN_INTROSPECTION_URL, status=401, json={})

        assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_not_json(menshen_backend_conf):
    """A response Drive cannot parse should defer to the next backend."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            MENSHEN_INTROSPECTION_URL,
            body="not json",
            content_type="text/plain",
        )

        assert MenshenAuthentication().authenticate(build_request()) is None


def test_menshen_authenticate_introspection_unknown_field(menshen_backend_conf):
    """A response carrying a field Drive's client ignores should defer, not crash."""
    with responses.RequestsMock() as rsps:
        introspection_mock(rsps, some_field_from_a_newer_menshen="unknown-field")

        assert MenshenAuthentication().authenticate(build_request()) is None


# Refusing the request


def test_menshen_authenticate_active_token_without_sub(menshen_backend_conf):
    """An active token that identifies no subject should be refused."""
    with responses.RequestsMock() as rsps:
        introspection_mock(rsps, sub=None)

        with pytest.raises(exceptions.AuthenticationFailed):
            MenshenAuthentication().authenticate(build_request())


def test_menshen_authenticate_inactive_user(menshen_backend_conf):
    """A disabled account should be refused."""
    factories.UserFactory(sub=MENSHEN_SUB, is_active=False)

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        with pytest.raises(exceptions.AuthenticationFailed):
            MenshenAuthentication().authenticate(build_request())


def test_menshen_authenticate_unknown_sub_without_user_creation(menshen_backend_conf):
    """No account should be provisioned while OIDC_CREATE_USER is off."""
    menshen_backend_conf.OIDC_CREATE_USER = False

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        with pytest.raises(exceptions.AuthenticationFailed):
            MenshenAuthentication().authenticate(build_request())

    assert not models.User.objects.filter(sub=MENSHEN_SUB).exists()


def test_menshen_authenticate_email_already_used(menshen_backend_conf):
    """A sub Drive does not know should not claim the email of an existing account."""
    factories.UserFactory(email=MENSHEN_EMAIL)

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        with pytest.raises(exceptions.AuthenticationFailed):
            MenshenAuthentication().authenticate(build_request())

    assert not models.User.objects.filter(sub=MENSHEN_SUB).exists()


def test_menshen_authenticate_email_already_used_in_another_case(menshen_backend_conf):
    """The email of an existing account should be matched case insensitively."""
    factories.UserFactory(email=MENSHEN_EMAIL.upper())

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        with pytest.raises(exceptions.AuthenticationFailed):
            MenshenAuthentication().authenticate(build_request())

    assert not models.User.objects.filter(sub=MENSHEN_SUB).exists()


def test_menshen_authenticate_duplicate_emails_allowed(menshen_backend_conf):
    """A deployment allowing duplicate emails should accept the new account."""
    menshen_backend_conf.OIDC_ALLOW_DUPLICATE_EMAILS = True
    factories.UserFactory(email=MENSHEN_EMAIL)

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        user, _payload = MenshenAuthentication().authenticate(build_request())

    assert user.sub == MENSHEN_SUB
    assert models.User.objects.filter(email__iexact=MENSHEN_EMAIL).count() == 2



# Authenticating the subject of the token


def test_menshen_authenticate_known_user(menshen_backend_conf):
    """An active token should authenticate the user matching its subject."""
    user = factories.UserFactory(sub=MENSHEN_SUB)

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        authenticated, payload = MenshenAuthentication().authenticate(build_request())

    assert authenticated == user
    assert payload["sub"] == MENSHEN_SUB
    assert models.User.objects.count() == 1


@pytest.mark.parametrize("scheme", ["bearer", "Bearer", "BEARER"])
def test_menshen_authenticate_scheme_is_case_insensitive(menshen_backend_conf, scheme):
    """The Authorization scheme should be matched case insensitively."""
    user = factories.UserFactory(sub=MENSHEN_SUB)

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        authenticated, _payload = MenshenAuthentication().authenticate(
            build_request(scheme=scheme)
        )

    assert authenticated == user


def test_menshen_authenticate_creates_the_user(menshen_backend_conf):
    """A subject Drive has never seen should be provisioned from the token claims.

    Menshen forwards the sub and the email of the subject token:
    a provisioned account carries no name and no claims.
    """
    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

        user, _payload = MenshenAuthentication().authenticate(build_request())

    assert user.sub == MENSHEN_SUB
    assert user.email == MENSHEN_EMAIL
    assert user.has_usable_password() is False
    assert user.claims == {}


def test_menshen_authenticate_does_not_update_the_known_user(menshen_backend_conf):
    """An exchanged token should not rewrite the email of an existing account."""
    user = factories.UserFactory(sub=MENSHEN_SUB, email="other@example.com")

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps)

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
def test_menshen_authenticate_exposes_the_scopes_as_a_list(menshen_backend_conf, scope, expected):
    """The space separated scope should reach the permissions as a list."""
    factories.UserFactory(sub=MENSHEN_SUB)

    with responses.RequestsMock() as rsps:
        introspection_mock(rsps, scope=scope)

        _user, payload = MenshenAuthentication().authenticate(build_request())

    assert payload["scope"] == expected


def test_menshen_authenticate_header_answers_401():
    """Unauthenticated request gets a 401."""
    assert MenshenAuthentication().authenticate_header(build_request()) == "bearer"

