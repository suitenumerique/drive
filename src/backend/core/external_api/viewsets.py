"""Resource Server Viewsets for the Drive app."""

from django.conf import settings
from django.db import transaction

import rest_framework as drf
from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from core import models
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
from core.entitlements import get_entitlements_backend
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

    permission_classes = [ResourceServerClientPermission & ItemPermission]

    @property
    def resource_server_actions(self):
        """Build resource_server_actions from settings."""
        return self._get_resource_server_actions("items")

    def get_create_extra_attributes(self):
        """Apply per-audience item attributes from EXTERNAL_API_AUD_ITEM_ATTRIBUTES."""
        audience = getattr(self.request, "resource_server_token_audience", None)
        return dict(settings.EXTERNAL_API_AUD_ITEM_ATTRIBUTES.get(audience) or {})

    owner_email = None

    def get_create_owner(self):
        """Resolve the user given by owner_email, or the token user when absent."""
        owner_email = self.request.data.get("owner_email")
        if not owner_email:
            return self.request.user

        try:
            self.owner_email = drf.serializers.EmailField().run_validation(owner_email)
        except drf.exceptions.ValidationError as excpt:
            raise drf.exceptions.ValidationError({"owner_email": excpt.detail}) from excpt

        try:
            owner = models.User.objects.get(email__iexact=self.owner_email)
        except models.User.DoesNotExist as excpt:
            raise drf.exceptions.ValidationError(
                {"owner_email": "No user matches this email."},
                code="item_create_on_behalf_unknown_email",
            ) from excpt
        except models.User.MultipleObjectsReturned as excpt:
            raise drf.exceptions.ValidationError(
                {"owner_email": "Several users share this email."},
                code="item_create_on_behalf_ambiguous_email",
            ) from excpt

        can_upload = get_entitlements_backend().can_upload(owner)
        if not can_upload["result"]:
            raise drf.exceptions.PermissionDenied(
                detail=can_upload.get("message", "This user cannot upload files."),
                code=can_upload.get("reason"),
            )
        return owner

    @transaction.atomic
    def perform_create(self, serializer):
        """Keep an owner access for the token user when creating on behalf of another user."""
        super().perform_create(serializer)
        item = serializer.instance
        if item.creator_id == self.request.user.id:
            return

        models.ItemAccess.objects.create(
            item=item,
            user=self.request.user,
            role=models.RoleChoices.OWNER,
        )


class ResourceServerUserViewSet(ResourceServerRestrictionMixin, UserViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & IsSelf]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("users")


class ResourceServerItemAccessViewSet(ResourceServerRestrictionMixin, ItemAccessViewSet):
    """Resource Server Viewset for ItemAccess."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("item_access")


class ResourceServerInvitationViewSet(ResourceServerRestrictionMixin, InvitationViewset):
    """Resource Server Viewset for Invitations."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & InvitationPermission]

    @property
    def resource_server_actions(self):
        """Get resource_server_actions from settings."""
        return self._get_resource_server_actions("item_invitation")
