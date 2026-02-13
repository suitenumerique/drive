"""WOPI viewsets module."""

import logging
import uuid
from os.path import splitext

from django.conf import settings
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
from core.mounts.providers.base import MountProviderError
from core.mounts.registry import get_mount_provider
from core.models import Item
from core.services.mount_capabilities import normalize_mount_capabilities
from core.utils.no_leak import safe_str_hash
from wopi.authentication import (
    WopiAccessTokenAuthentication,
    WopiMountAccessTokenAuthentication,
)
from wopi.permissions import AccessTokenPermission, MountAccessTokenPermission
from wopi.services.lock import LockService, MountLockService
from wopi.utils import compute_mount_entry_version

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


class MountWopiViewSet(viewsets.ViewSet):
    """
    WOPI ViewSet for mount-backed files.

    This endpoint family does not echo mount paths; operator-facing logs rely on
    safe correlation hashes.
    """

    authentication_classes = [WopiMountAccessTokenAuthentication]
    permission_classes = [MountAccessTokenPermission]

    detail_post_actions = {
        "LOCK": "_lock",
        "GET_LOCK": "_get_lock",
        "REFRESH_LOCK": "_refresh_lock",
        "UNLOCK": "_unlock",
    }

    def get_file_id(self):
        """Get the file id from the URL path."""
        return uuid.UUID(self.kwargs.get("pk"))

    def _enabled_mount(self, mount_id: str) -> dict | None:
        mounts = list(getattr(settings, "MOUNTS_REGISTRY", []) or [])
        for mount in mounts:
            if not bool(mount.get("enabled", True)):
                continue
            if mount.get("mount_id") == mount_id:
                return mount
        return None

    def _mount_capabilities(self, mount: dict) -> dict[str, bool]:
        params = mount.get("params") if isinstance(mount.get("params"), dict) else {}
        return normalize_mount_capabilities((params or {}).get("capabilities"))

    def _wopi_mount_or_none(self, mount_id: str) -> dict | None:
        mount = self._enabled_mount(mount_id)
        if not mount:
            return None
        if not bool(self._mount_capabilities(mount).get("mount.wopi")):
            return None
        return mount

    def _provider_for_mount(self, mount: dict):
        provider = get_mount_provider(str(mount.get("provider") or ""))
        if not (hasattr(provider, "open_read") and hasattr(provider, "open_write")):
            return None
        return provider

    def _stat_file(
        self,
        *,
        provider,
        mount: dict,
        mount_id: str,
        normalized_path: str,
    ):
        try:
            entry = provider.stat(mount=mount, normalized_path=normalized_path)
        except MountProviderError as exc:
            logger.info(
                "mount_wopi_stat: failed "
                "(failure_class=%s next_action_hint=%s mount_id=%s path_hash=%s)",
                exc.failure_class,
                exc.next_action_hint,
                mount_id,
                safe_str_hash(normalized_path),
            )
            status_code = 404 if exc.public_code == "mount.path.not_found" else 500
            return None, status_code

        if entry.entry_type != "file":
            return None, 404

        return entry, 200

    # pylint: disable=unused-argument
    def retrieve(self, request, pk=None):
        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")

        mount = self._wopi_mount_or_none(mount_id)
        provider = self._provider_for_mount(mount) if mount else None
        if not (mount and provider):
            return Response(status=404)

        entry, status_code = self._stat_file(
            provider=provider,
            mount=mount,
            mount_id=mount_id,
            normalized_path=normalized_path,
        )
        if not entry:
            return Response(status=status_code)

        version = compute_mount_entry_version(entry)
        size = 0 if entry.size is None else int(entry.size)

        return Response(
            {
                "BaseFileName": str(entry.name or "file"),
                "OwnerId": mount_id,
                "IsAnonymousUser": request.user.is_anonymous,
                "UserFriendlyName": request.user.full_name
                if not request.user.is_anonymous
                else None,
                "Size": size,
                "UserId": str(request.user.id),
                "Version": version,
                "UserCanWrite": True,
                "UserCanRename": False,
                "UserCanPresent": False,
                "UserCanAttend": False,
                "UserCanNotWriteRelative": True,
                "ReadOnly": False,
                "SupportsRename": False,
                "SupportsUpdate": True,
                "SupportsDeleteFile": False,
                "SupportsCobalt": False,
                "SupportsContainers": False,
                "SupportsEcosystem": False,
                "SupportsGetFileWopiSrc": False,
                "SupportsGetLock": True,
                "SupportsLocks": True,
                "SupportsUserInfo": False,
            },
            status=200,
        )

    @action(detail=True, methods=["get", "post"], url_path="contents")
    def file_content(self, request, pk=None):
        if request.method == "GET":
            return self._get_file_content(request, pk)
        if request.method == "POST":
            return self._put_file_content(request, pk)
        return Response(status=405)

    def _get_file_content(self, request, pk=None):
        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")

        mount = self._wopi_mount_or_none(mount_id)
        provider = self._provider_for_mount(mount) if mount else None
        if not (mount and provider):
            return Response(status=404)

        entry, status_code = self._stat_file(
            provider=provider,
            mount=mount,
            mount_id=mount_id,
            normalized_path=normalized_path,
        )
        if not entry:
            return Response(status=status_code)

        max_expected_size = request.META.get("HTTP_X_WOPI_MAXEXPECTEDSIZE")
        if max_expected_size and entry.size is not None:
            if int(entry.size) > int(max_expected_size):
                return Response(status=412)

        chunk_size = 64 * 1024

        def _stream():
            try:
                with provider.open_read(
                    mount=mount, normalized_path=normalized_path
                ) as f:
                    while True:
                        data = f.read(chunk_size)
                        if not data:
                            break
                        yield data
            except MountProviderError as exc:
                logger.info(
                    "mount_wopi_get_file: failed "
                    "(failure_class=%s next_action_hint=%s mount_id=%s path_hash=%s)",
                    exc.failure_class,
                    exc.next_action_hint,
                    mount_id,
                    safe_str_hash(normalized_path),
                )
                return
            except (OSError, ValueError):
                return

        headers = {"X-WOPI-ItemVersion": compute_mount_entry_version(entry)}
        if entry.size is not None:
            headers["Content-Length"] = str(int(entry.size))

        return StreamingHttpResponse(
            streaming_content=_stream(),
            content_type="application/octet-stream",
            headers=headers,
            status=200,
        )

    @staticmethod
    def _lock_conflict_response(*, current_lock_value: str):
        return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

    def _put_file_content(self, request, pk=None):
        if request.META.get(HTTP_X_WOPI_OVERRIDE) != "PUT":
            return Response(status=404)

        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")

        mount = self._wopi_mount_or_none(mount_id)
        provider = self._provider_for_mount(mount) if mount else None
        if not (mount and provider):
            return Response(status=404)

        lock_service = MountLockService(mount_id=mount_id, normalized_path=normalized_path)
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)

        if lock_value:
            current_lock_value = lock_service.get_lock(default="")
            if current_lock_value != lock_value:
                return self._lock_conflict_response(
                    current_lock_value=current_lock_value
                )
        else:
            body_size = int(request.META.get("CONTENT_LENGTH") or 0)
            if body_size > 0:
                return self._lock_conflict_response(current_lock_value="")

        status_code = 200
        bytes_written = 0
        version = None

        try:
            chunk_size = 64 * 1024
            stream = getattr(request, "_request", request)
            with provider.open_write(mount=mount, normalized_path=normalized_path) as f:
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    f.write(chunk)
            entry, stat_status = self._stat_file(
                provider=provider,
                mount=mount,
                mount_id=mount_id,
                normalized_path=normalized_path,
            )
            if not entry:
                status_code = stat_status
            else:
                version = compute_mount_entry_version(entry)
        except RequestDataTooBig:
            status_code = 413
        except MountProviderError as exc:
            logger.info(
                "mount_wopi_put_file: failed "
                "(failure_class=%s next_action_hint=%s mount_id=%s path_hash=%s)",
                exc.failure_class,
                exc.next_action_hint,
                mount_id,
                safe_str_hash(normalized_path),
            )
            status_code = 500
        except (OSError, ValueError) as exc:
            logger.info(
                "mount_wopi_put_file: failed "
                "(failure_class=mount.wopi.save_failed "
                "next_action_hint=Verify mount provider connectivity and retry "
                "mount_id=%s path_hash=%s)",
                mount_id,
                safe_str_hash(normalized_path),
            )
            capture_exception(exc)
            status_code = 500

        if status_code != 200 or not version:
            return Response(status=status_code)

        logger.info(
            "mount_wopi_put_file: ok (mount_id=%s path_hash=%s size=%sB)",
            mount_id,
            safe_str_hash(normalized_path),
            bytes_written,
        )
        return Response(status=200, headers={X_WOPI_ITEMVERSION: version})

    def detail_post(self, request, pk=None):
        if not request.META.get(HTTP_X_WOPI_OVERRIDE) in self.detail_post_actions:
            return Response(status=404)
        post_action = self.detail_post_actions[request.META.get(HTTP_X_WOPI_OVERRIDE)]
        return getattr(self, post_action)(request, pk)

    def _lock(self, request, pk=None):
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)
        if not lock_value:
            return Response(status=400)

        if request.META.get(HTTP_X_WOPI_OLD_LOCK, False):
            return self._unlock_and_relock(request, pk)

        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")
        if not self._wopi_mount_or_none(mount_id):
            return Response(status=404)

        lock_service = MountLockService(mount_id=mount_id, normalized_path=normalized_path)
        if not lock_service.is_locked():
            lock_service.lock(lock_value)
            return Response(status=200)

        if not lock_service.is_lock_valid(lock_value):
            return Response(status=409, headers={X_WOPI_LOCK: lock_service.get_lock()})

        lock_service.refresh_lock()
        return Response(status=200)

    def _get_lock(self, request, pk=None):
        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")
        if not self._wopi_mount_or_none(mount_id):
            return Response(status=404)

        lock_service = MountLockService(mount_id=mount_id, normalized_path=normalized_path)
        return Response(
            status=200, headers={X_WOPI_LOCK: lock_service.get_lock(default="")}
        )

    def _refresh_lock(self, request, pk=None):
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)
        if not lock_value:
            return Response(status=400)

        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")
        if not self._wopi_mount_or_none(mount_id):
            return Response(status=404)

        lock_service = MountLockService(mount_id=mount_id, normalized_path=normalized_path)
        current_lock_value = lock_service.get_lock(default="")
        if current_lock_value != lock_value:
            return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        lock_service.refresh_lock()
        return Response(status=200)

    def _unlock(self, request, pk=None):
        lock_value = request.META.get(HTTP_X_WOPI_LOCK)
        if not lock_value:
            return Response(status=400)

        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")
        if not self._wopi_mount_or_none(mount_id):
            return Response(status=404)

        lock_service = MountLockService(mount_id=mount_id, normalized_path=normalized_path)
        current_lock_value = lock_service.get_lock(default="")
        if current_lock_value != lock_value:
            return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        lock_service.unlock()
        return Response(status=200)

    def _unlock_and_relock(self, request, pk=None):
        old_lock_value = request.META.get(HTTP_X_WOPI_OLD_LOCK)
        new_lock_value = request.META.get(HTTP_X_WOPI_LOCK)
        if not old_lock_value or not new_lock_value:
            return Response(status=400)

        ctx = request.auth
        mount_id = str(getattr(ctx, "mount_id", "") or "").strip()
        normalized_path = str(getattr(ctx, "normalized_path", "") or "")
        if not self._wopi_mount_or_none(mount_id):
            return Response(status=404)

        lock_service = MountLockService(mount_id=mount_id, normalized_path=normalized_path)
        current_lock_value = lock_service.get_lock(default="")
        if current_lock_value != old_lock_value:
            return Response(status=409, headers={X_WOPI_LOCK: current_lock_value})

        lock_service.unlock()
        lock_service.lock(new_lock_value)
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
