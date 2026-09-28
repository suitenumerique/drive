"""Test the rename file operation from the WOPI viewset."""

from io import BytesIO
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.test import override_settings

import botocore
import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService
from wopi.viewsets import X_WOPI_INVALIDFILENAMERROR, X_WOPI_LOCK

pytestmark = pytest.mark.django_db


def request_rename(filename, requested_name):
    """Create a file and request a WOPI rename."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename=filename,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    access_token, _ = AccessUserItemService().insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"content"))

    response = APIClient().post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
            "X-WOPI-RequestedName": requested_name,
        },
    )
    return item, response


def test_rename_file_success():
    """User having access to the item can rename the file."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    default_storage.save(item.file_key, BytesIO(b"my prose"))
    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
            "X-WOPI-RequestedName": "new name".encode("utf-7").decode("ascii"),
        },
    )
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.filename == "new name.txt"
    assert item.title == "new name"

    assert len(response.content) == 0


def test_rename_file_success_accept_json():
    """User having access to the item can rename the file."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    default_storage.save(item.file_key, BytesIO(b"my prose"))
    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
            "X-WOPI-RequestedName": "new name".encode("utf-7").decode("ascii"),
            "Accept": "application/json",
        },
    )
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.filename == "new name.txt"
    assert item.title == "new name"
    assert response.json()["Name"] == "new name"


def test_rename_file_no_filename():
    """Request without X-WOPI-RequestedName header should return 400."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
        },
    )
    assert response.status_code == 400
    assert response.headers.get(X_WOPI_INVALIDFILENAMERROR) == "No filename provided"


def test_rename_file_duplicate_filename():
    """User cannot rename file to an existing filename."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="new_name.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
            "X-WOPI-RequestedName": "new_name",
        },
    )
    assert response.status_code == 400
    assert response.headers.get(X_WOPI_INVALIDFILENAMERROR) == "Filename already exists"


def test_rename_file_with_lock():
    """User can rename file when providing a valid lock."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    default_storage.save(item.file_key, BytesIO(b"my prose"))

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    lock_service = LockService(item)
    lock_service.lock("1234567890")

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
            "X-WOPI-RequestedName": "new_name",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.filename == "new_name.txt"
    assert item.title == "new_name"


def test_rename_file_with_invalid_lock():
    """User cannot rename file when providing an invalid lock."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    lock_service = LockService(item)
    lock_service.lock("1234567890")

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "RENAME_FILE",
            "X-WOPI-RequestedName": "new_name",
            "X-WOPI-Lock": "invalid-lock",
        },
    )
    assert response.status_code == 409
    assert response.headers.get(X_WOPI_LOCK) == "1234567890"


@pytest.mark.parametrize("requested_name", ["bridge+AC8-", "bridge+AFw-"])
def test_rename_file_rejects_path_separator(requested_name):
    """A path separator decoded from UTF-7 should make the filename invalid."""
    item, response = request_rename("wopi_test.txt", requested_name)

    assert response.status_code == 400
    assert response.headers.get(X_WOPI_INVALIDFILENAMERROR) == "Invalid filename"
    item.refresh_from_db()
    assert item.filename == "wopi_test.txt"


def test_rename_file_rejects_disallowed_target_extension():
    """An extensionless file cannot be renamed to acquire a disallowed extension."""
    item, response = request_rename("wopi_test", "malware.exe")

    assert response.status_code == 400
    assert response.headers.get(X_WOPI_INVALIDFILENAMERROR) == "This file extension is not allowed"
    item.refresh_from_db()
    assert item.filename == "wopi_test"


@override_settings(RESTRICT_UPLOAD_FILE_TYPE=True, FILE_EXTENSIONS_ALLOWED=[".STEP"])
def test_rename_file_allows_extension_case_insensitively():
    """Allowed extensions should be matched case-insensitively."""
    item, response = request_rename("model.STEP", "renamed")

    assert response.status_code == 200
    item.refresh_from_db()
    assert item.filename == "renamed.STEP"


def test_rename_file_storage_error():
    """File rename should fail when storage operation fails."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        title="wopi_test",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    default_storage.save(item.file_key, BytesIO(b"my prose"))

    client = APIClient()
    with (
        patch.object(
            default_storage.connection.meta.client,
            "copy_object",
            side_effect=botocore.exceptions.ClientError(
                {"Error": {"Code": "StorageError", "Message": "Storage error"}},
                "copy_object",
            ),
        ),
        pytest.raises(botocore.exceptions.ClientError),
    ):
        client.post(
            f"/api/v1.0/wopi/files/{item.id}/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            headers={
                "X-WOPI-Override": "RENAME_FILE",
                "X-WOPI-RequestedName": "new_name",
            },
        )

    item.refresh_from_db()
    assert item.filename == "wopi_test.txt"  # Original filename unchanged
    assert item.title == "wopi_test"  # Original title unchanged
