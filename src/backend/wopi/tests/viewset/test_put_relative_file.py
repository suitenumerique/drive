"""Test the put relative file operation from the WOPI viewset."""

from io import BytesIO
from unittest.mock import patch

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


def test_put_relative_file_suggested_target_extension_only():
    """
    When X-WOPI-SuggestedTarget starts with ".", the new filename is built by
    replacing the original extension: base_name + suggested_target.
    """
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

    client = APIClient()
    suggested = ".pdf".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": suggested,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "document.pdf"
    assert "Url" in data
    assert "HostEditUrl" in data

    item.refresh_from_db()
    assert item.filename == "document.pdf"
    assert item.title == "document.pdf"
    assert item.size == len(b"pdf content")

    s3_client = default_storage.connection.meta.client
    obj = s3_client.get_object(Bucket=default_storage.bucket_name, Key=item.file_key)
    assert obj["Body"].read() == b"pdf content"


def test_put_relative_file_suggested_target_full_filename():
    """
    When X-WOPI-SuggestedTarget does not start with ".", the value is used
    as the complete new filename.
    """
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

    client = APIClient()
    suggested = "converted_document.pdf".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": suggested,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "converted_document.pdf"

    item.refresh_from_db()
    assert item.filename == "converted_document.pdf"
    assert item.title == "converted_document.pdf"


def test_put_relative_file_relative_target():
    """
    When X-WOPI-RelativeTarget is provided, the value is used as the exact
    new filename.
    """
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

    client = APIClient()
    relative = "exact_name.pdf".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-RelativeTarget": relative,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "exact_name.pdf"

    item.refresh_from_db()
    assert item.filename == "exact_name.pdf"
    assert item.title == "exact_name.pdf"


def test_put_relative_file_response_contains_wopi_url_with_access_token():
    """The response Url must include a fresh access_token query parameter."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

    client = APIClient()
    suggested = ".pdf".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": suggested,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 200
    assert "access_token=" in response.json()["Url"]


def test_put_relative_file_response_contains_host_edit_url():
    """The response HostEditUrl must point to /wopi/<item_id>."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

    client = APIClient()
    suggested = ".pdf".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": suggested,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 200
    assert f"/wopi/{item.id}" in response.json()["HostEditUrl"]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_put_relative_file_missing_file_conversion_header():
    """Request without X-WOPI-FileConversion header must return 400."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.odt",
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
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": ".pdf".encode("utf-7").decode("ascii"),
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["details"] == "only file conversion is supported."


def test_put_relative_file_both_targets_provided():
    """Providing both X-WOPI-SuggestedTarget and X-WOPI-RelativeTarget must return 400."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.odt",
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
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": ".pdf".encode("utf-7").decode("ascii"),
            "X-WOPI-RelativeTarget": "name.pdf".encode("utf-7").decode("ascii"),
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["details"] == (
        "both HTTP_X_WOPI_SUGGESTEDTARGET and HTTP_X_WOPI_RELATIVETARGET are mutually exclusive."
    )


def test_put_relative_file_no_target_provided():
    """Providing neither X-WOPI-SuggestedTarget nor X-WOPI-RelativeTarget must return 400."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.odt",
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
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["details"] == (
        "both HTTP_X_WOPI_SUGGESTEDTARGET and HTTP_X_WOPI_RELATIVETARGET are mutually exclusive."
    )


def test_put_relative_file_user_without_write_access():
    """A user with read-only access must receive 401."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.READER)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": ".pdf".encode("utf-7").decode("ascii"),
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 401


def test_put_relative_file_request_body_too_large():
    """When the request body is too large, a 413 must be returned."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    with patch(
        "wopi.viewsets.ContentFile",
        side_effect=__import__(
            "django.core.exceptions", fromlist=["RequestDataTooBig"]
        ).RequestDataTooBig,
    ):
        response = client.post(
            f"/api/v1.0/wopi/files/{item.id}/",
            data=b"pdf content",
            content_type="application/octet-stream",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            headers={
                "X-WOPI-Override": "PUT_RELATIVE",
                "X-WOPI-SuggestedTarget": ".pdf".encode("utf-7").decode("ascii"),
                "X-WOPI-FileConversion": "1",
            },
        )

    assert response.status_code == 413


def test_put_relative_file_no_access_token():
    """Request without an access token must be rejected (403)."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="wopi_test.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": ".pdf".encode("utf-7").decode("ascii"),
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 403


def test_put_relative_file_wrong_item_access_token():
    """
    An access token tied to a different item must not allow the operation (403).
    """
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    other_item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="other_document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.EDITOR)
    factories.UserItemAccessFactory(item=other_item, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/wopi/files/{other_item.id}/",
        data=b"pdf content",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-SuggestedTarget": ".pdf".encode("utf-7").decode("ascii"),
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 403
