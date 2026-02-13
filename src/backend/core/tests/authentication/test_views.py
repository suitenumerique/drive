"""Unit tests for the Authentication Views."""

from unittest import mock

from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.csrf import CsrfViewMiddleware
from django.test import RequestFactory
from django.test.utils import override_settings

import posthog
import pytest
from lasuite.oidc_login.views import (
    OIDCAuthenticationCallbackView as LaSuiteOIDCAuthenticationCallbackView,
)
from mozilla_django_oidc.auth import (
    OIDCAuthenticationBackend as MozillaOIDCAuthenticationBackend,
)

from core import factories
from core.authentication.backends import OIDCAuthenticationBackend
from core.authentication.exceptions import UserCannotAccessApp
from core.authentication.views import (
    OIDCAuthenticationCallbackView,
)

pytestmark = pytest.mark.django_db


@override_settings(
    LOGIN_REDIRECT_URL_FAILURE="/auth/failure",
    LOGIN_REDIRECT_URL="/auth/success",
)
@mock.patch.object(
    MozillaOIDCAuthenticationBackend,
    "get_token",
    return_value={"id_token": "mocked_id_token", "access_token": "mocked_access_token"},
)
@mock.patch.object(
    MozillaOIDCAuthenticationBackend, "verify_token", return_value={"not": "needed"}
)
@mock.patch.object(
    OIDCAuthenticationBackend,
    "get_userinfo",
    return_value={"sub": "mocked_sub", "email": "allowed@example.com"},
)
@mock.patch.object(posthog, "feature_enabled", return_value=False)
def test_view_login_callback_authorized_by_default(
    mocked_feature_enabled, mocked_get_userinfo, mocked_verify_token, mocked_get_token
):
    """By default, all users are authorized to login."""

    user = factories.UserFactory(email="allowed@example.com")

    request = RequestFactory().get(
        "/callback/", data={"state": "mocked_state", "code": "mocked_code"}
    )
    request.user = user

    middleware = SessionMiddleware(get_response=lambda x: x)
    middleware.process_request(request)

    mocked_state = "mocked_state"
    request.session["oidc_states"] = {mocked_state: {"nonce": "mocked_nonce"}}
    request.session.save()

    callback_view = OIDCAuthenticationCallbackView.as_view()

    response = callback_view(request)
    mocked_get_token.assert_called_once()
    mocked_verify_token.assert_called_once()
    mocked_get_userinfo.assert_called_once()
    mocked_feature_enabled.assert_not_called()
    assert response.status_code == 302
    assert response.url == "/auth/success"

    response = CsrfViewMiddleware(get_response=lambda r: r).process_response(
        request, response
    )
    assert response.cookies.get("csrftoken")


@override_settings(
    LOGIN_REDIRECT_URL_FAILURE="/auth/failure",
    LOGIN_REDIRECT_URL="/auth/success",
)
@mock.patch.object(
    LaSuiteOIDCAuthenticationCallbackView,
    "get",
    side_effect=UserCannotAccessApp("Uploads are disabled for this user."),
)
def test_view_login_callback_denied_includes_safe_message(mocked_super_get):
    """Denied users should be redirected with a safe, operator-actionable hint."""
    request = RequestFactory().get("/callback/")
    middleware = SessionMiddleware(get_response=lambda x: x)
    middleware.process_request(request)
    request.session.save()

    callback_view = OIDCAuthenticationCallbackView.as_view()
    response = callback_view(request)

    mocked_super_get.assert_called_once()
    assert response.status_code == 302
    assert response.url.startswith("/auth/failure?")
    assert "auth_error=user_cannot_access_app" in response.url
    assert "auth_error_message=" in response.url
