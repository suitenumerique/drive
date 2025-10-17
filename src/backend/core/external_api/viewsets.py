"""Resource Server Viewsets for the Drive app."""

import rest_framework as drf
from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from core.api.permissions import IsAuthenticated, ItemAccessPermission
from core.api.viewsets import ItemViewSet, UserViewSet
from core.external_api.permissions import ResourceServerClientPermission


class ResourceServerItemViewSet(ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]

    resource_server_actions = ["list", "retrieve", "children", "upload_ended"]


class ResourceServerUserViewSet(UserViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission]

    resource_server_actions = ["get_me"]

    @drf.decorators.action(
        detail=False,
        methods=["get"],
        url_name="me",
        url_path="me",
        permission_classes=[IsAuthenticated & ResourceServerClientPermission],
    )
    def get_me(self, request):
        """Get the current user."""
        return super().get_me(request)
