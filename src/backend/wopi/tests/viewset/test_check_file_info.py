"""Testing the check file info endpoint"""

from io import BytesIO

from django.contrib.auth.models import AnonymousUser
from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService

pytestmark = pytest.mark.django_db


def test_check_file_info_connected_user_with_access():
    """User having access to the item can get the file info with write permissions."""
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
    head_response = default_storage.connection.meta.client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.get(
        f"/api/v1.0/wopi/files/{item.id}/", HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "BaseFileName": item.filename,
        "OwnerId": str(item.creator.id),
        "IsAnonymousUser": False,
        "UserFriendlyName": user.full_name,
        "Size": 8,
        "UserId": str(user.id),
        "Version": head_response["VersionId"],
        "UserCanWrite": True,
        "UserCanRename": True,
        "UserCanPresent": False,
        "UserCanAttend": False,
        "UserCanNotWriteRelative": True,
        "ReadOnly": False,
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


def test_check_file_info_connected_user_reader_access():
    """User with reader access to the item can get the file info with read permissions."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.READER
    )

    default_storage.save(item.file_key, BytesIO(b"my prose"))
    head_response = default_storage.connection.meta.client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.get(
        f"/api/v1.0/wopi/files/{item.id}/", HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "BaseFileName": item.filename,
        "OwnerId": str(item.creator.id),
        "IsAnonymousUser": False,
        "UserFriendlyName": user.full_name,
        "Size": 8,
        "UserId": str(user.id),
        "Version": head_response["VersionId"],
        "UserCanWrite": False,
        "UserCanRename": False,
        "UserCanPresent": False,
        "UserCanAttend": False,
        "UserCanNotWriteRelative": True,
        "ReadOnly": True,
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


def test_check_file_info_connected_user_reader_access_deleted_item():
    """Item is deleted, user with reader access to the item can't get the file info."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.READER
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    item.soft_delete()

    client = APIClient()
    response = client.get(
        f"/api/v1.0/wopi/files/{item.id}/", HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    assert response.status_code == 403


def test_check_file_info_anonymous_user_with_access():
    """Anonymous user having access to the item can get the file info with read permissions."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
    )
    user = AnonymousUser()

    default_storage.save(item.file_key, BytesIO(b"my prose"))
    head_response = default_storage.connection.meta.client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.get(
        f"/api/v1.0/wopi/files/{item.id}/", HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "BaseFileName": item.filename,
        "OwnerId": str(item.creator.id),
        "IsAnonymousUser": True,
        "UserFriendlyName": None,
        "Size": 8,
        "UserId": str(user.id),
        "Version": head_response["VersionId"],
        "UserCanWrite": False,
        "UserCanRename": False,
        "UserCanPresent": False,
        "UserCanAttend": False,
        "UserCanNotWriteRelative": True,
        "ReadOnly": True,
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


def test_check_file_info_non_existing_access_token():
    """Non existing access token should return 401."""
    item = factories.ItemFactory()
    client = APIClient()
    response = client.get(
        f"/api/v1.0/wopi/files/{item.id}/",
        HTTP_AUTHORIZATION="Bearer not_existing_token",
    )
    assert response.status_code == 403
