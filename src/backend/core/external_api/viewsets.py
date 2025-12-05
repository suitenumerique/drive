"""Resource Server Viewsets for the Drive app."""

from django.conf import settings

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from core.api.permissions import ItemAccessPermission
from core.api.viewsets import (
    InvitationViewset,
    ItemAccessViewSet,
    ItemViewSet,
    UserViewSet,
)
from core.external_api.permissions import ResourceServerClientPermission

# pylint: disable=too-many-ancestors


class ResourceServerItemViewSet(ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]

    @property
    def resource_server_actions(self):
        """Build resource_server_actions from settings."""
        items_config = settings.EXTERNAL_API.get("items", {})
        return list(items_config.get("actions", []))


class ResourceServerUserViewSet(UserViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission]

    resource_server_actions = ["get_me"]


class ResourceServerItemAccessViewSet(ItemAccessViewSet):
    """Resource Server Viewset for ItemAccess."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        item_access_config = settings.EXTERNAL_API.get("item_access", {})
        return list(item_access_config.get("actions", []))


class ResourceServerInvitationViewSet(InvitationViewset):
    """Resource Server Viewset for Invitations."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        item_invitation_config = settings.EXTERNAL_API.get("item_invitation", {})
        return list(item_invitation_config.get("actions", []))
