"""Resource Server Viewsets for the Drive app."""

from django.conf import settings

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
from core.external_api.authentication import MenshenAuthentication, ResourceServerAuthentication
from core.external_api.permissions import MenshenPermission, ResourceServerClientPermission

# pylint: disable=too-many-ancestors


class ResourceServerRestrictionMixin:
    """Restrict a resource server viewset to the actions EXTERNAL_API opens for its resource.

    Subclasses declare `resource`, the EXTERNAL_API key of the resource they serve.
    """

    @property
    def resource_server_actions(self):
        """Actions EXTERNAL_API opens for this viewset's resource."""
        return list(settings.EXTERNAL_API.get(self.resource, {}).get("actions", []))

    def get_permissions(self):
        """Apply the external API checks to every action, whatever its permission classes.

        MenshenPermission only passes requests authenticated by MenshenAuthentication,
        so it opens nothing on a viewset that does not list that backend.
        """
        return [
            (MenshenPermission | ResourceServerClientPermission)(),
            *super().get_permissions(),
        ]


class ResourceServerItemViewSet(ResourceServerRestrictionMixin, ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [MenshenAuthentication, ResourceServerAuthentication]

    permission_classes = [ItemPermission]
    resource = "items"

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
    resource = "users"


class ResourceServerItemAccessViewSet(ResourceServerRestrictionMixin, ItemAccessViewSet):
    """Resource Server Viewset for ItemAccess."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ItemAccessPermission]
    resource = "item_access"


class ResourceServerInvitationViewSet(ResourceServerRestrictionMixin, InvitationViewset):
    """Resource Server Viewset for Invitations."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [InvitationPermission]
    resource = "item_invitation"
