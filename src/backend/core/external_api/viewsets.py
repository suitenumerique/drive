"""Resource Server Viewsets for the Drive app."""

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from core.api.permissions import ItemAccessPermission
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
