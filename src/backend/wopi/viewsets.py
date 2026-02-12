"""WOPI viewsets module."""

import logging
import uuid
from os.path import splitext

from django.core.exceptions import RequestDataTooBig
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import StreamingHttpResponse

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from sentry_sdk import capture_exception

from core.api.utils import get_item_file_head_object
from core.models import Item
from wopi.authentication import WopiAccessTokenAuthentication
from wopi.permissions import AccessTokenPermission
from wopi.services.lock import LockService

logger = logging.getLogger(__name__)


HTTP_X_WOPI_LOCK = "HTTP_X_WOPI_LOCK"
HTTP_X_WOPI_OLD_LOCK = "HTTP_X_WOPI_OLDLOCK"
HTTP_X_WOPI_OVERRIDE = "HTTP_X_WOPI_OVERRIDE"

X_WOPI_INVALIDFILENAMERROR = "X-WOPI-InvalidFileNameError"
X_WOPI_ITEMVERSION = "X-WOPI-ItemVersion"
X_WOPI_LOCK = "X-WOPI-Lock"


class WopiViewSet(viewsets.ViewSet):
    """
    WOPI ViewSet
    """

    authentication_classes = [WopiAccessTokenAuthentication]
    permission_classes = [AccessTokenPermission]
    queryset = Item.objects.all()

    detail_post_actions = {
        "LOCK": "_lock",
        "GET_LOCK": "_get_lock",
        "REFRESH_LOCK": "_refresh_lock",
        "UNLOCK": "_unlock",
        "RENAME_FILE": "_rename_file",
    }

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

    @action(detail=True, methods=["get", "post"], url_path="contents")
    def file_content(self, request, pk=None):
        """
        Operations to get or put the file content.
        """
        if request.method == "GET":
            return self._get_file_content(request, pk)
        if request.method == "POST":
            return self._put_file_content(request, pk)

        return Response(status=405)

    def _get_file_content(self, request, pk=None):
        """
        Implementation of the Wopi GetFile file operation
        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/getfile
        """
        item = request.auth.item

        max_expected_size = request.META.get("HTTP_X_WOPI_MAXEXPECTEDSIZE")

        head_object = get_item_file_head_object(item)
        if max_expected_size:
            if int(head_object["ContentLength"]) > int(max_expected_size):
                return Response(status=412)

        s3_client = default_storage.connection.meta.client

        file = s3_client.get_object(
            Bucket=default_storage.bucket_name,
            Key=item.file_key,
        )

        return StreamingHttpResponse(
            streaming_content=file["Body"].iter_chunks(),
            content_type=item.mimetype,
            headers={
                "X-WOPI-ItemVersion": head_object["VersionId"],
                "Content-Length": head_object["ContentLength"],
            },
            status=200,
        )

    def _put_file_content(self, request, pk=None):
        """
        Implementation of the Wopi PutFile file operation
        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/putfile
        """

        if request.META.get(HTTP_X_WOPI_OVERRIDE) != "PUT":
            return Response(status=404)

        item = request.auth.item
        abilities = item.get_abilities(request.user)

        if not abilities["update"]:
            return Response(status=401)

        lock_value = request.META.get(HTTP_X_WOPI_LOCK)

        if lock_value:
            lock_service = LockService(item)
            current_lock_value = lock_service.get_lock(default="")
            if current_lock_value != lock_value:
                return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})
        else:
            # Check if the body is 0 bytes
            body_size = int(request.META.get("CONTENT_LENGTH") or 0)
            if body_size > 0:
                return Response(status=409, headers={X_WOPI_LOCK: ""})

        try:
            file = ContentFile(request.body)
        except RequestDataTooBig:
            return Response(status=413)

        s3_client = default_storage.connection.meta.client
        default_storage.save(item.file_key, file)
        item.size = file.size
        item.save(update_fields=["size", "updated_at"])

        head_response = s3_client.head_object(
            Bucket=default_storage.bucket_name, Key=item.file_key
        )
        return Response(
            status=200, headers={X_WOPI_ITEMVERSION: head_response["VersionId"]}
        )

    def detail_post(self, request, pk=None):
        """
        A details view acessible using a POST request.
        WOPI protocol uses multiple time this POST view for different actions.
        The action is determined by the X-WOPI-Override header.
        The actions are:
        - LOCK: Acquire a lock on the file
        - GET_LOCK: Retrieve a lock on the file
        - REFRESH_LOCK: Refresh a lock on the file
        - UNLOCK: Release a lock on the file
        - RENAME_FILE: Rename the file
        """
        if not request.META.get(HTTP_X_WOPI_OVERRIDE) in self.detail_post_actions:
            return Response(status=404)
        item = request.auth.item
        abilities = item.get_abilities(request.user)

        if not abilities["update"]:
            return Response(status=401)

        post_action = self.detail_post_actions[request.META.get(HTTP_X_WOPI_OVERRIDE)]
        return getattr(self, post_action)(request, pk)

    def _lock(self, request, pk=None):
        """
        Acquire a lock on the file

        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/lock
        """
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)

        if not lock_value:
            return Response(status=400)

        if request.META.get(HTTP_X_WOPI_OLD_LOCK, False):
            return self._unlock_and_relock(request, pk)

        item = request.auth.item
        lock_service = LockService(item)

        if not lock_service.is_locked():
            lock_service.lock(lock_value)
            return Response(status=200)

        if not lock_service.is_lock_valid(lock_value):
            return Response(status=409, headers={X_WOPI_LOCK: lock_service.get_lock()})

        lock_service.refresh_lock()
        return Response(status=200)

    def _get_lock(self, request, pk=None):
        """
        Retrieve a lock on the file

        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/getlock
        """
        item = request.auth.item
        lock_service = LockService(item)

        return Response(
            status=200, headers={X_WOPI_LOCK: lock_service.get_lock(default="")}
        )

    def _refresh_lock(self, request, pk=None):
        """
        Refresh a lock on the file

        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/refreshlock
        """
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)

        if not lock_value:
            return Response(status=400)

        item = request.auth.item
        lock_service = LockService(item)

        current_lock_value = lock_service.get_lock(default="")

        if current_lock_value != lock_value:
            return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        lock_service.refresh_lock()
        return Response(status=200)

    def _unlock(self, request, pk=None):
        """
        Release a lock on the file

        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/unlock
        """
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)

        if not lock_value:
            return Response(status=400)

        item = request.auth.item
        lock_service = LockService(item)

        current_lock_value = lock_service.get_lock(default="")

        if current_lock_value != lock_value:
            return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        lock_service.unlock()
        return Response(status=200)

    def _unlock_and_relock(self, request, pk=None):
        """
        Release a lock on the file and lock it again.

        https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/files/unlockandrelock
        """
        old_lock_value = request.META.get(HTTP_X_WOPI_OLD_LOCK)
        new_lock_value = request.META.get(HTTP_X_WOPI_LOCK)

        if not old_lock_value or not new_lock_value:
            return Response(status=400)

        item = request.auth.item
        lock_service = LockService(item)

        current_lock_value = lock_service.get_lock(default="")
        if current_lock_value != old_lock_value:
            return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        lock_service.unlock()
        lock_service.lock(new_lock_value)
        return Response(status=200)

    def _rename_file(self, request, pk=None):
        """
        Rename the file
        """
        item = request.auth.item
        abilities = item.get_abilities(request.user)

        if not abilities["update"]:
            return Response(status=401)

        new_filename = request.META.get("HTTP_X_WOPI_REQUESTEDNAME")

        if not new_filename:
            return Response(
                status=400,
                headers={X_WOPI_INVALIDFILENAMERROR: "No filename provided"},
            )

        # Convert it to utf-7 to avoid issues with special characters
        new_filename = new_filename.encode("ascii").decode("utf-7")
        lock_service = LockService(item)
        if lock_service.is_locked():
            current_lock_value = lock_service.get_lock(default="")
            lock_value = request.META.get(HTTP_X_WOPI_LOCK)
            if current_lock_value != lock_value:
                return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        _, current_extension = splitext(item.filename)
        new_filename_with_extension = f"{new_filename}{current_extension}"

        parent_path = item.path[:-1]
        # Filter on siblings with the desired filename
        queryset = (
            Item.objects.filter(path__descendants=".".join(parent_path))
            .filter(path__depth=item.depth)
            .filter(filename=new_filename_with_extension)
            .exclude(id=item.id)
        )

        if queryset.exists():
            return Response(
                status=400,
                headers={X_WOPI_INVALIDFILENAMERROR: "Filename already exists"},
            )
        head_object = get_item_file_head_object(item)

        file_key = item.file_key
        item.filename = new_filename_with_extension
        item.title = new_filename

        # ensure renaming the file in the database and on the storage are done atomically
        with transaction.atomic():
            item.save(update_fields=["filename", "title", "updated_at"])

            # Rename the file in the storage
            s3_client = default_storage.connection.meta.client
            # Don't catch any s3 error, if failing let the exception raises to sentry
            # the transaction will be rolled back
            s3_client.copy_object(
                Bucket=default_storage.bucket_name,
                CopySource={
                    "Bucket": default_storage.bucket_name,
                    "Key": file_key,
                },
                Key=item.file_key,
                MetadataDirective="COPY",
            )

        try:
            s3_client.delete_object(
                Bucket=default_storage.bucket_name,
                Key=file_key,
                VersionId=head_object["VersionId"],
            )
        # pylint: disable=broad-exception-caught
        except Exception as e:  # noqa
            capture_exception(e)
            logger.warning(
                "Error deleting old file for item %s in the storage: %s", item.id, e
            )

        if "application/json" in request.META.get("HTTP_ACCEPT", ""):
            return Response(
                data={"Name": new_filename}, status=200, content_type="application/json"
            )

        return Response(status=200)
