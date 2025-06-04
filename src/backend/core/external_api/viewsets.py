"""Resource Server Viewsets for the Drive app."""

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from ..api.permissions import AccessPermission, ItemAccessPermission
from ..api.viewsets import ItemAccessViewSet, ItemViewSet
from .authentication import JWTAuthentication
from .permissions import ResourceServerClientPermission

# pylint: disable=too-many-ancestors


class ResourceServerItemViewSet(ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [JWTAuthentication, ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]


class ResourceServerItemAccessViewSet(ItemAccessViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [JWTAuthentication, ResourceServerAuthentication]

    permission_classes = [ResourceServerClientPermission & AccessPermission]
