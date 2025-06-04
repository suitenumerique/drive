"""Resource Server Viewsets for the Drive app."""

from ..api.permissions import AccessPermission, IsAuthenticated, ItemAccessPermission
from ..api.viewsets import ItemAccessViewSet, ItemViewSet
from .authentication import JWTAuthentication

# pylint: disable=too-many-ancestors


class ExternalItemViewSet(ItemViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [JWTAuthentication]

    permission_classes = [IsAuthenticated & ItemAccessPermission]


class ExternalItemAccessViewSet(ItemAccessViewSet):
    """Resource Server Viewset for the Drive app."""

    authentication_classes = [JWTAuthentication]

    permission_classes = [IsAuthenticated & AccessPermission]
