"""Authentication for WOPI requests."""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from wopi.services.access import AccessError, AccessUserItemService


def get_access_token(request):
    """Look for the access_token in both headers and query params."""
    access_token = request.headers.get(
        "Authorization", request.query_params.get("access_token")
    )

    if access_token and access_token.startswith("Bearer "):
        access_token = access_token[7:]

    return access_token


class WopiAccessTokenAuthentication(BaseAuthentication):
    """
    WOPI access token authentication.
    """

    def authenticate(self, request):
        """
        Authenticate the request.
        """
        # First check if the access token is present in the request
        access_token = get_access_token(request)
        if not access_token:
            raise AuthenticationFailed("Access token not provided")

        # Check if the access token exists in cache
        service = AccessUserItemService()
        try:
            access_user_item = service.get_access_user_item(access_token)
        except AccessError as err:
            raise AuthenticationFailed("Invalid access token") from err

        return (access_user_item.user, access_user_item)
