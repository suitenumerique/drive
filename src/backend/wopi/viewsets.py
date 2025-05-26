"""WOPI viewsets module."""

import logging
import uuid

from rest_framework import viewsets
from rest_framework.response import Response

from core.api.utils import get_item_file_head_object
from core.models import Item
from wopi.authentication import WopiAccessTokenAuthentication
from wopi.permissions import AccessTokenPermission

logger = logging.getLogger(__name__)


class WopiViewSet(viewsets.ViewSet):
    """
    WOPI ViewSet
    """

    authentication_classes = [WopiAccessTokenAuthentication]
    permission_classes = [AccessTokenPermission]
    queryset = Item.objects.all()

    def get_file_id(self):
        """Get the file id from the URL path."""
        return uuid.UUID(self.kwargs.get("pk"))

    # pylint: disable=unused-argument
    def retrieve(self, request, pk=None):
        """
        Implementation of the Wopi CheckFileInfo file operation
        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/checkfileinfo
        """
        item = request.auth.item
        abilities = item.get_abilities(request.user)

        head_object = get_item_file_head_object(item)

        properties = {
            "BaseFileName": item.filename,
            "OwnerId": str(item.creator.id),
            "IsAnonymousUser": request.user.is_anonymous,
            "UserFriendlyName": request.user.full_name
            if not request.user.is_anonymous
            else None,
            "Size": head_object["ContentLength"],
            "UserId": str(request.user.id),
            "Version": head_object.get("VersionId", ""),
            "UserCanWrite": abilities["update"],
            "UserCanRename": abilities["update"],
            "UserCanPresent": False,
            "UserCanAttend": False,
            "UserCanNotWriteRelative": True,
            "ReadOnly": not abilities["update"],
            "SupportsRename": True,
            "SupportsUpdate": True,
            "SupportsDeleteFile": True,
            "SupportsCobalt": False,
            "SupportsContainers": False,
            "SupportsEcosystem": False,
            "SupportsGetFileWopiSrc": False,
            "SupportsGetLock": True,
            "SupportsLocks": True,
            "SupportsUserInfo": False,
            "DownloadUrl": f"/media/{item.file_key}",
        }
        return Response(properties, status=200)
