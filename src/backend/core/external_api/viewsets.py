"""Resource Server Viewsets for the Drive app."""

from django.conf import settings

from lasuite.oidc_resource_server.authentication import ResourceServerAuthentication

from ..api.permissions import AccessPermission, ItemAccessPermission
from ..api.viewsets import ItemAccessViewSet, ItemViewSet
from .authentication import JWTAuthentication
from .permissions import ResourceServerClientPermission

# pylint: disable=too-many-ancestors


if settings.JWT_AUTH_ENABLED:
    EXTERNAL_API_AUTH_CLASSES = [JWTAuthentication, ResourceServerAuthentication]
else:
    EXTERNAL_API_AUTH_CLASSES = [ResourceServerAuthentication]


class ResourceServerItemViewSet(ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = EXTERNAL_API_AUTH_CLASSES

    permission_classes = [ResourceServerClientPermission & ItemAccessPermission]


class ResourceServerItemAccessViewSet(ItemAccessViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = EXTERNAL_API_AUTH_CLASSES

    permission_classes = [ResourceServerClientPermission & AccessPermission]
