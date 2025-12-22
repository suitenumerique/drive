"""Resource Server Viewsets for the Drive app."""

from django.conf import settings

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from core.api.permissions import AccessPermission, IsSelf, ItemAccessPermission
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


class ResourceServerItemViewSet(ResourceServerRestrictionMixin, ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]

    @property
    def resource_server_actions(self):
        """Build resource_server_actions from settings."""
        return self._get_resource_server_actions("items")


class ResourceServerUserViewSet(ResourceServerRestrictionMixin, UserViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & IsSelf]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("users")


class ResourceServerItemAccessViewSet(
    ResourceServerRestrictionMixin, ItemAccessViewSet
):
    """Resource Server Viewset for ItemAccess."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & AccessPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("item_access")


class ResourceServerInvitationViewSet(
    ResourceServerRestrictionMixin, InvitationViewset
):
    """Resource Server Viewset for Invitations."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & AccessPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("item_invitation")
