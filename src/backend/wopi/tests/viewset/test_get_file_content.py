"""Test the Wopi GetFileContent viewset."""

from io import BytesIO

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService

pytestmark = pytest.mark.django_db


def test_get_file_content_connected_user_with_access():
    """User having access to the item can get the file content."""
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
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert response.status_code == 200
    assert response.streaming_content
    assert response.headers["X-WOPI-ItemVersion"] == head_response["VersionId"]
    assert response.headers["Content-Length"] == "8"


def test_get_file_content_connected_user_not_linked_to_item():
    """
    User trying to get the file content of an item not linked to the access token should get a 403.
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
    response = client.get(
        f"/api/v1.0/wopi/files/{other_item.id}/contents/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert response.status_code == 403


def test_get_file_content_max_expected_size():
    """
    User trying to get the file content of an item with a max expected size should get a 412 if
    the file is too large.
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

    default_storage.save(item.file_key, BytesIO(b"my prose"))

    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.get(
        f"/api/v1.0/wopi/files/{item.id}/contents/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_WOPI_MAXEXPECTEDSIZE="2",
    )
    assert response.status_code == 412
