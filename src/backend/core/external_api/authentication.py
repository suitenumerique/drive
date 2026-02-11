"""Resource Server authentication wrappers (no-leak)."""

from lasuite.oidc_resource_server.authentication import (
    ResourceServerAuthentication as UpstreamResourceServerAuthentication,
)
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated


class DriveResourceServerAuthentication(UpstreamResourceServerAuthentication):
    """Sanitize authentication errors to stay generic and no-leak for clients."""

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except NotAuthenticated as err:
            raise NotAuthenticated(
                "Authentication credentials were not provided."
            ) from err
        except AuthenticationFailed as err:
            raise AuthenticationFailed("Invalid authentication credentials.") from err
