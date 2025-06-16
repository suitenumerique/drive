"""Resource Server Viewsets for the Drive app."""

from knox.auth import TokenAuthentication
from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from ..api.permissions import AccessPermission, ItemAccessPermission
from ..api.viewsets import ItemAccessViewSet, ItemViewSet
from .permissions import ResourceServerClientPermission

# pylint: disable=too-many-ancestors


class ResourceServerItemViewSet(ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [TokenAuthentication, ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]


class ResourceServerItemAccessViewSet(ItemAccessViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & AccessPermission]
