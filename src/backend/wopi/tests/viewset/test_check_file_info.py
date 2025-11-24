"""Testing the check file info endpoint"""

from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core.files.storage import default_storage
from django.utils.timezone import now

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.exceptions import WopiRequestSignatureError
from wopi.services.access import AccessUserItemService
from wopi.utils import signature as signature_utils

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

    upload_file = default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
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
        "Version": upload_file["VersionId"],
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

    upload_file = default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
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
        "Version": upload_file["VersionId"],
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

    upload_file = default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
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
        "Version": upload_file["VersionId"],
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


def test_check_file_info_connected_user_with_access_with_valid_signature(
    configure_wopi_clients,
):
    """Check signature validation for a connected user with access."""
    wopi_configuration = configure_wopi_clients
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
        mimetype="text/plain",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    wopi_timestamp = (
        signature_utils.DOTNET_EPOCH_TICKS
        + now().timestamp() * signature_utils.TICKS_PER_SECOND
    )

    client = APIClient()
    with mock.patch.object(
        signature_utils, "verify_wopi_proof"
    ) as mock_verify_wopi_proof:
        mock_verify_wopi_proof.return_value = True
        response = client.get(
            f"/api/v1.0/wopi/files/{item.id}/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            HTTP_X_WOPI_PROOF="valid_signature",
            HTTP_X_WOPI_TIMESTAMP=wopi_timestamp,
        )

    assert response.status_code == 200

    mock_verify_wopi_proof.assert_called_once_with(
        wopi_configuration["vendorA"]["proof_keys"],
        "valid_signature",
        None,
        mock.ANY,
    )


def test_check_file_info_connected_user_with_access_with_invalid_signature(
    configure_wopi_clients,
):
    """Check signature validation for a connected user with access."""
    wopi_configuration = configure_wopi_clients
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
        mimetype="text/plain",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    wopi_timestamp = (
        signature_utils.DOTNET_EPOCH_TICKS
        + now().timestamp() * signature_utils.TICKS_PER_SECOND
    )

    client = APIClient()
    with mock.patch.object(
        signature_utils, "verify_wopi_proof"
    ) as mock_verify_wopi_proof:
        mock_verify_wopi_proof.return_value = False
        with pytest.raises(
            WopiRequestSignatureError, match="Invalid request signature"
        ):
            client.get(
                f"/api/v1.0/wopi/files/{item.id}/",
                HTTP_AUTHORIZATION=f"Bearer {access_token}",
                HTTP_X_WOPI_PROOF="invalid_signature",
                HTTP_X_WOPI_TIMESTAMP=wopi_timestamp,
            )

    mock_verify_wopi_proof.assert_called_once_with(
        wopi_configuration["vendorA"]["proof_keys"],
        "invalid_signature",
        None,
        mock.ANY,
    )


def test_check_file_info_connected_user_with_access_with_expired_wopi_timestamp(
    configure_wopi_clients,  # pylint: disable=unused-argument
):
    """Check signature validation for a connected user with access with expired wopi timestamp."""
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
        mimetype="text/plain",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    wopi_timestamp = (
        signature_utils.DOTNET_EPOCH_TICKS
        + (now() - timedelta(minutes=20)).timestamp() * signature_utils.TICKS_PER_SECOND
    )

    client = APIClient()
    with mock.patch.object(
        signature_utils, "verify_wopi_proof"
    ) as mock_verify_wopi_proof:
        with pytest.raises(
            WopiRequestSignatureError, match="Timestamp is too old, request rejected"
        ):
            client.get(
                f"/api/v1.0/wopi/files/{item.id}/",
                HTTP_AUTHORIZATION=f"Bearer {access_token}",
                HTTP_X_WOPI_PROOF="invalid_signature",
                HTTP_X_WOPI_TIMESTAMP=wopi_timestamp,
            )

    mock_verify_wopi_proof.assert_not_called()


def test_check_file_info_connected_user_with_access_proof_keys_configured_but_no_signature_provided(
    configure_wopi_clients,  # pylint: disable=unused-argument
):
    """Check signature validation for a connected user with access with no signature provided."""
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
        mimetype="text/plain",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    with mock.patch.object(
        signature_utils, "verify_wopi_proof"
    ) as mock_verify_wopi_proof:
        with pytest.raises(
            WopiRequestSignatureError, match="No signature provided, request rejected"
        ):
            client.get(
                f"/api/v1.0/wopi/files/{item.id}/",
                HTTP_AUTHORIZATION=f"Bearer {access_token}",
            )

    mock_verify_wopi_proof.assert_not_called()


def test_check_file_info_connected_user_with_access_proof_keys_configured_but_no_timestamp_provided(
    configure_wopi_clients,  # pylint: disable=unused-argument
):
    """Check signature validation for a connected user with access with no timestamp provided."""
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
        mimetype="text/plain",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    default_storage.connection.meta.client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        Body=BytesIO(b"my prose"),
        ContentType="text/plain",
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    with mock.patch.object(
        signature_utils, "verify_wopi_proof"
    ) as mock_verify_wopi_proof:
        with pytest.raises(
            WopiRequestSignatureError, match="No timestamp provided, request rejected"
        ):
            client.get(
                f"/api/v1.0/wopi/files/{item.id}/",
                HTTP_AUTHORIZATION=f"Bearer {access_token}",
                HTTP_X_WOPI_PROOF="invalid_signature",
            )

    mock_verify_wopi_proof.assert_not_called()
