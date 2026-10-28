"""Authentication for the external API."""

import logging
from dataclasses import asdict
from functools import lru_cache

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation, ValidationError

import requests
from lasuite.oidc_resource_server.authentication import (
    ResourceServerAuthentication as LaSuiteResourceServerAuthentication,
)
from menshen_client import Configuration, IntrospectionRequest, TokenExchangeClient
from menshen_client.exceptions import ResponseParsingError
from rest_framework import authentication, exceptions

from core.authentication.backends import check_user_can_access
from core.authentication.exceptions import UserCannotAccessApp

User = get_user_model()
logger = logging.getLogger(__name__)


def get_token(request, token_type):
    """Extract the token from the Authorization header.

    Args:
        request: The incoming request
        token_type: Expected Authorization scheme (e.g. Bearer), matched
            case-insensitively

    Returns:
        Token string, or None if the request carries no token of this type

    Raises:
        AuthenticationFailed: If the Authorization header is malformed
    """

    auth_header = authentication.get_authorization_header(request).split()

    if not auth_header or auth_header[0].lower() != token_type.lower().encode():
        return None

    if len(auth_header) != 2:
        logger.warning("Invalid token header format")
        raise exceptions.AuthenticationFailed("Invalid token header.")

    try:
        return auth_header[1].decode("utf-8")
    except UnicodeError as e:
        logger.warning("Token decode error: %s", e)
        raise exceptions.AuthenticationFailed("Invalid token encoding.") from e

def get_or_create_user_by_sub(sub, email=None):
    """Retrieve the user matching a token sub, creating it if allowed.

    A token is never resolved to a user by email.

    Args:
        sub: Subject identifier from the introspected token
        email: Email to store on a newly created user

    Returns:
        User instance, or None if unknown and OIDC_CREATE_USER is unset

    Raises:
        SuspiciousOperation: If the sub is missing or invalid, the email of a user
            to create is already used, or the user account is disabled
    """

    if not sub:
        raise SuspiciousOperation("User info did not provide a sub")

    try:
        User.sub_validator(sub)
    except ValidationError as err:
        raise SuspiciousOperation("User info contained an invalid sub claim") from err

    try:
        user = User.objects.get(sub=sub)
    except User.DoesNotExist:
        if not settings.OIDC_CREATE_USER:
            return None

        # A second account sharing this email would break the lookups by email that
        # the interactive login relies on: refuse to create one.
        if (
            email
            and not settings.OIDC_ALLOW_DUPLICATE_EMAILS
            and User.objects.filter(email__iexact=email).exists()
        ):
            logger.warning("Email already used, not creating user: %s", sub)
            raise SuspiciousOperation("Email already used by another account.") from None

        user = User(sub=sub, email=email)
        user.set_unusable_password()
        user.save()

    if not user.is_active:
        logger.warning("Inactive user attempted authentication: %s", user.pk)
        raise SuspiciousOperation("User account is disabled.")

    return user

@lru_cache(1)
def _get_token_exchange_client():
    return TokenExchangeClient(
        config=Configuration(
            settings.MENSHEN_CLIENT_ID,
            settings.MENSHEN_CLIENT_SECRET,
            settings.MENSHEN_SERVER_URL,
        )
    )


class MenshenAuthentication(authentication.BaseAuthentication):
    """Authentication for tokens exchanged through Menshen.

    Menshen is La Suite's OAuth 2.0 token exchange server (RFC 8693): another service
    exchanges its user's access token for a token targeting Drive, then calls the external
    API on behalf of that user. Tokens are validated by introspection (RFC 7662). Menshen
    only reports a token as active when Drive is among its audiences.
    """

    def authenticate(self, request):
        """Introspect the bearer token with Menshen.

        Returns:
            Tuple of (user, payload) if the token is active, None otherwise
        """

        if not settings.MENSHEN_ENABLED:
            return None

        token = get_token(request, "bearer")

        if token is None:
            return None

        client = _get_token_exchange_client()

        try:
            response = client.introspect(IntrospectionRequest(token=token))
        except (requests.RequestException, ResponseParsingError) as e:
            logger.warning("Menshen introspection failed: %s", e)
            return None

        # Permission classes expect a dict payload in request.auth.
        payload = asdict(response)

        if not payload.get("active"):
            # Not a Menshen token, or an expired or revoked one: defer to next
            # authentication backend
            return None

        user = self.get_or_create_user(payload)

        # Menshen reports the service that exchanged the token as its client_id, which is
        # what the resource server path reports as the token audience.
        request.resource_server_token_audience = payload.get("client_id")

        scopes = payload.get("scope") or ""
        payload["scope"] = scopes.split()

        return (user, payload)

    def get_or_create_user(self, payload):
        """Retrieve or create the user from the introspection response.

        Menshen forwards the `sub` and `email` of the subject token, as introspected
        with the OIDC provider.

        Args:
            payload: Introspection response dict

        Returns:
            User instance

        Raises:
            AuthenticationFailed: If user not found or inactive
            PermissionDenied: If the entitlements backend refuses the user access
        """

        sub = payload.get("sub")

        if not sub:
            logger.warning("Missing 'sub' in Menshen introspection response")
            raise exceptions.AuthenticationFailed("Invalid token claims.")

        try:
            user = get_or_create_user_by_sub(sub, email=payload.get("email"))
        except SuspiciousOperation as e:
            raise exceptions.AuthenticationFailed(str(e)) from e

        if user is None:
            logger.warning("User not found: %s", sub)
            raise exceptions.AuthenticationFailed("User not found.")

        try:
            check_user_can_access(user)
        except UserCannotAccessApp as e:
            logger.warning("User not entitled to access the app: %s", user.pk)
            raise exceptions.PermissionDenied(str(e)) from e

        return user

    def authenticate_header(self, request):
        """Return authentication scheme for WWW-Authenticate header."""
        return "bearer"


class ResourceServerAuthentication(LaSuiteResourceServerAuthentication):
    """Authentication for tokens introspected with the OIDC provider."""

    def authenticate(self, request):
        """Defer to the next authentication backend when the resource server is off."""

        if not settings.OIDC_RESOURCE_SERVER_ENABLED:
            return None

        return super().authenticate(request)
