"""Server-to-server authentication with user impersonation."""

from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core import models


class ServerToServerUserAuthentication(BaseAuthentication):
    """
    Authenticate trusted applications with a static bearer token and impersonate
    the acting user passed in the "X-User-Sub" / "X-User-Email" headers.

    Returns None when the bearer token is not a known server-to-server token so
    the next authentication classes (OIDC, session) get a chance to run.
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split(" ")

        if len(parts) != 2 or parts[0] != "Bearer":
            return None

        if parts[1] not in settings.SERVER_TO_SERVER_API_TOKENS:
            return None

        sub = request.headers.get("X-User-Sub")
        email = request.headers.get("X-User-Email")

        if not sub and not email:
            # The calling application acts for an anonymous visitor: abilities
            # are computed with public-link semantics only.
            return (AnonymousUser(), "s2s")

        user = None
        if sub:
            user = models.User.objects.filter(sub=sub).first()
        if user is None and email:
            user = models.User.objects.filter(email__iexact=email).first()

        if user is None:
            raise AuthenticationFailed("Unknown acting user for server-to-server request.")

        return (user, "s2s")
