"""Test the PUT file content viewset."""

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


def test_put_file_content_connected_user_with_access():
    """User having access to the item can put file content."""
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
        size=0,
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
    assert item.size == 0
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 200
    assert "X-WOPI-ItemVersion" in response.headers

    # Verify the content was actually updated
    s3_client = default_storage.connection.meta.client
    file = s3_client.get_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
    )
    assert file["Body"].read() == b"new content"
    assert response.headers.get("X-WOPI-ItemVersion") == file["VersionId"]
    item.refresh_from_db()
    assert item.size == 11  # the size should have been updated


def test_put_file_content_connected_user_with_access_delete_item_during_edition():
    """User should not be able to put file content if the item is deleted during the edition."""
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
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 200
    assert "X-WOPI-ItemVersion" in response.headers

    # Verify the content was actually updated
    s3_client = default_storage.connection.meta.client
    file = s3_client.get_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
    )
    assert file["Body"].read() == b"new content"
    assert response.headers.get("X-WOPI-ItemVersion") == file["VersionId"]

    item.soft_delete()

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"rejected content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 403

    # Verify the content was not updated
    s3_client = default_storage.connection.meta.client
    file = s3_client.get_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
    )
    assert (
        file["Body"].read() == b"new content"
    )  # the content should not have been updated


def test_put_file_content_connected_user_with_access_access_removed_during_edition():
    """
    User should not be able to put file content if the user loses access to the item during the
    edition.
    """
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
    user = factories.UserFactory()
    access = factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.EDITOR
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    lock_service = LockService(item)
    lock_service.lock("1234567890")

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 200
    assert "X-WOPI-ItemVersion" in response.headers

    # Verify the content was actually updated
    s3_client = default_storage.connection.meta.client
    file = s3_client.get_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
    )
    assert file["Body"].read() == b"new content"
    assert response.headers.get("X-WOPI-ItemVersion") == file["VersionId"]

    access.delete()

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"rejected content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
            "X-WOPI-Lock": "1234567890",
        },
    )
    assert response.status_code == 403

    # Verify the content was not updated
    s3_client = default_storage.connection.meta.client
    file = s3_client.get_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
    )
    assert (
        file["Body"].read() == b"new content"
    )  # the content should not have been updated


def test_put_file_content_connected_user_not_linked_to_item():
    """
    User trying to put file content of an item not linked to the access token should get a 403.
    """
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

    other_item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="other_wopi_test.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.UserItemAccessFactory(
        item=other_item, user=user, role=models.RoleChoices.EDITOR
    )

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{other_item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
        },
    )
    assert response.status_code == 403


def test_put_file_content_without_override_header():
    """Request without X-WOPI-OVERRIDE header should return 404."""
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
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert response.status_code == 404


def test_put_file_content_with_invalid_lock():
    """User cannot put file content when providing an invalid lock."""
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

    # try to put content with an invalid lock
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
            "X-WOPI-Lock": "invalid-lock",
        },
    )
    assert response.status_code == 409
    assert response.headers.get("X-WOPI-Lock") == "1234567890"


def test_put_file_content_with_no_lock_header_and_body_size_greater_than_0():
    """
    User cannot put file content when not providing a lock header and the body size
    is greater than 0.
    """
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
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"new content",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
        },
    )
    assert response.status_code == 409
    assert response.headers.get("X-WOPI-Lock") == ""


def test_put_file_content_with_no_lock_header_and_body_size_0():
    """User can put file content when not providing a lock header and the body size is 0."""
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
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        data=b"",
        content_type="text/plain",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-WOPI-ItemVersion") is not None

    # Verify the content was actually updated
    s3_client = default_storage.connection.meta.client
    file = s3_client.get_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
    )
    assert file["Body"].read() == b""
    assert response.headers.get("X-WOPI-ItemVersion") == file["VersionId"]
