"""Resource Server Permissions for the Drive app."""

from django.conf import settings

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication
from rest_framework import permissions

from core.external_api.authentication import MenshenAuthentication


class MenshenPermission(permissions.BasePermission):
    """
    Permission class for resource server views, using token exchange Menshen.
    """
    def has_permission(self, request, view):
        """
        Check if the user is authenticated and the token introspection
        provides an authorized Service Provider and required scopes.
        """

        if not isinstance(request.successful_authenticator, MenshenAuthentication):
            # Not a Menshen token exchange request
            return False

        action = getattr(view, "action", None)
        if not action:
            # Let DRF routers return a 405 for unsupported methods
            return True

        if hasattr(view, "resource_server_actions") and action not in view.resource_server_actions:
            return False

        required_scope = settings.MENSHEN_REQUIRED_SCOPES.get(
            getattr(view, "resource", None), {}
        ).get(action)

        # required_scope can be str or dict mapping method to scope
        if isinstance(required_scope, dict):
            required_scope = required_scope.get(request.method)

        if not required_scope:
            # An action left out of the mapping is never reachable with an exchanged token
            return False

        return required_scope in ((request.auth or {}).get("scope") or [])


class ResourceServerClientPermission(permissions.BasePermission):
    """
    Permission class for resource server views.
    This provides a way to open the resource server views to a limited set of
    Service Providers.
    Note: See MenshenPermission for more complex permission system, based on
    the Service Provider ID and the requested scopes.
    """

    def has_permission(self, request, view):
        """
        Check if the user is authenticated and the token introspection
        provides an authorized Service Provider.
        """
        if not isinstance(request.successful_authenticator, ResourceServerAuthentication):
            # Not a resource server request
            return False

        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return False

        if (
            hasattr(view, "resource_server_actions")
            and view.action not in view.resource_server_actions
        ):
            return False

        # When used as a resource server, the request has a token audience
        return request.resource_server_token_audience in settings.OIDC_RS_ALLOWED_AUDIENCES
