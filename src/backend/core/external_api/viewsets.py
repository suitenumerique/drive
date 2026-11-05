"""Resource Server Viewsets for the Drive app."""

from django.conf import settings

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from core.api.permissions import (
    InvitationPermission,
    IsSelf,
    ItemAccessPermission,
    ItemPermission,
)
from core.api.viewsets import (
    InvitationViewset,
    ItemAccessViewSet,
    ItemViewSet,
    UserViewSet,
)
from core.external_api.permissions import ResourceServerClientPermission

# pylint: disable=too-many-ancestors


class ResourceServerRestrictionMixin:
    """
    Mixin for Resource Server Viewsets to provide shortcut to get
    configured actions for a given resource.
    """

    def _get_resource_server_actions(self, resource_name):
        """Get resource_server_actions from settings."""
        external_api_config = settings.EXTERNAL_API.get(resource_name, {})
        return list(external_api_config.get("actions", []))

    def get_permissions(self):
        """Apply the resource server checks to every action, whatever its permission classes."""
        return [ResourceServerClientPermission(), *super().get_permissions()]


class ResourceServerItemViewSet(ResourceServerRestrictionMixin, ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ItemPermission]

    @property
    def resource_server_actions(self):
        """Build resource_server_actions from settings."""
        return self._get_resource_server_actions("items")

    def get_create_extra_attributes(self):
        """Apply per-audience item attributes from EXTERNAL_API_AUD_ITEM_ATTRIBUTES."""
        audience = getattr(self.request, "resource_server_token_audience", None)
        attributes = dict(settings.EXTERNAL_API_AUD_ITEM_ATTRIBUTES.get(audience) or {})
        if audience:
            # The audience is the client_id of the token (OIDC_RS_AUDIENCE_CLAIM claim,
            # or client_id reported by Menshen introspection).
            attributes.setdefault("source", audience)
        return attributes


class ResourceServerUserViewSet(ResourceServerRestrictionMixin, UserViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [IsSelf]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("users")


class ResourceServerItemAccessViewSet(ResourceServerRestrictionMixin, ItemAccessViewSet):
    """Resource Server Viewset for ItemAccess."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ItemAccessPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("item_access")


class ResourceServerInvitationViewSet(ResourceServerRestrictionMixin, InvitationViewset):
    """Resource Server Viewset for Invitations."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [InvitationPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("item_invitation")
