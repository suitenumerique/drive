"""Test the rename file operation from the WOPI viewset."""

from io import BytesIO
from unittest.mock import patch

from django.core.files.storage import default_storage

import botocore
import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService
from wopi.viewsets import X_WOPI_INVALIDFILENAMERROR, X_WOPI_LOCK

pytestmark = pytest.mark.django_db


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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )
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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

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
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

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
