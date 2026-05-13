"""Test the put relative file operation from the WOPI viewset."""

import copy
from io import BytesIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.services.access import AccessUserItemService
from wopi.services.lock import LockService

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Success cases
# ---------------------------------------------------------------------------


def test_put_relative_file_suggested_target_extension_only():
    """
    When X-WOPI-SuggestedTarget starts with ".", a new item is created with the
    original base name and the suggested extension, and its title is prefixed
    with "Conversion of". The original item is kept intact.
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
    original = copy.copy(item)

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
    assert data["Name"] == "Conversion of document.pdf"
    assert "Url" in data
    assert "HostEditUrl" in data

    item.refresh_from_db()
    assert item.filename == "document.odt"
    assert item.title == original.title
    assert item.size == original.size
    assert item.mimetype == original.mimetype

    s3_client = default_storage.connection.meta.client
    obj = s3_client.get_object(Bucket=default_storage.bucket_name, Key=original.file_key)
    assert obj["Body"].read() == b"original content"

    new_item = models.Item.objects.exclude(id=item.id).get(
        filename="Conversion of document.pdf", type=models.ItemTypeChoices.FILE
    )
    assert new_item.title == new_item.filename == "Conversion of document.pdf"
    assert new_item.size == len(b"pdf content")
    assert new_item.upload_state == models.ItemUploadStateChoices.READY
    new_obj = s3_client.get_object(Bucket=default_storage.bucket_name, Key=new_item.file_key)
    assert new_obj["Body"].read() == b"pdf content"


def test_put_relative_file_suggested_target_full_filename():
    """
    When X-WOPI-SuggestedTarget does not start with ".", the value is used as
    the complete new filename of a freshly created item.
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
    assert item.filename == "document.odt"

    new_item = models.Item.objects.exclude(id=item.id).get(filename="converted_document.pdf")
    assert new_item.title == "converted_document.pdf"


def test_put_relative_file_relative_target():
    """
    When X-WOPI-RelativeTarget is provided, the value is used as the exact
    filename of a freshly created item.
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
    assert item.filename == "document.odt"

    new_item = models.Item.objects.exclude(id=item.id).get(filename="exact_name.pdf")
    assert new_item.title == "exact_name.pdf"


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
    new_item = models.Item.objects.exclude(id=item.id).get(filename="Conversion of document.pdf")
    parsed = urlparse(response.json()["Url"])
    assert parsed.path.rstrip("/") == f"/api/v1.0/wopi/files/{new_item.id}"
    query = parse_qs(parsed.query)
    assert query.get("access_token") not in (None, [""])


def test_put_relative_file_response_contains_host_edit_url():
    """The response HostEditUrl must point to the converted item, not the source."""
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
    new_item = models.Item.objects.exclude(id=item.id).get(filename="Conversion of document.pdf")
    assert f"/wopi/{new_item.id}" in response.json()["HostEditUrl"]
    assert f"/wopi/{item.id}" not in response.json()["HostEditUrl"]


def test_put_relative_file_creates_in_parent_when_user_can_write_there():
    """The converted item is placed in the source parent when the user can write there."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

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

    assert response.status_code == 200
    new_item = models.Item.objects.exclude(id=item.id).get(filename="Conversion of document.pdf")
    assert new_item.parent() == folder
    assert not new_item.is_root


def test_put_relative_file_creates_in_user_root_when_no_parent_access():
    """Falls back to the user's root with OWNER when the source parent is not writable."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
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

    assert response.status_code == 200
    new_item = models.Item.objects.exclude(id=item.id).get(filename="Conversion of document.pdf")
    assert new_item.is_root
    assert new_item.accesses.filter(user=user, role=models.RoleChoices.OWNER).exists()


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
    assert response.json()["error"]["details"] == "Only file conversion is supported."


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
        "HTTP_X_WOPI_SUGGESTEDTARGET and HTTP_X_WOPI_RELATIVETARGET are mutually exclusive."
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
        "One of HTTP_X_WOPI_SUGGESTEDTARGET or HTTP_X_WOPI_RELATIVETARGET must be provided."
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


def test_put_relative_file_relative_target_conflict():
    """RelativeTarget with an existing sibling filename must return 409."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        title="exact_name.pdf",
        filename="exact_name.pdf",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

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

    assert response.status_code == 409
    assert (
        models.Item.objects.filter(
            filename="exact_name.pdf", type=models.ItemTypeChoices.FILE
        ).count()
        == 1
    )


def test_put_relative_file_relative_target_conflict_with_lock():
    """RelativeTarget colliding with a locked item must return 409."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    existing = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        title="exact_name.pdf",
        filename="exact_name.pdf",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    LockService(existing).lock("lock-abc-123")
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)

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

    assert response.status_code == 409


def test_put_relative_file_suggested_target_disambiguates_collision():
    """A sibling named after the pre-prefix filename must not cause a collision."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        title="document.pdf",
        filename="document.pdf",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
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
    assert data["Name"] == "Conversion of document.pdf"
    new_item = models.Item.objects.get(filename=data["Name"], type=models.ItemTypeChoices.FILE)
    assert new_item.title == new_item.filename == "Conversion of document.pdf"


def test_put_relative_file_suggested_target_disambiguates_prefixed_collision():
    """SuggestedTarget must disambiguate against the final prefixed conversion name."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        title="Conversion of document.pdf",
        filename="Conversion of document.pdf",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(item, user)
    default_storage.save(item.file_key, BytesIO(b"original content"))

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

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] != "Conversion of document.pdf"
    assert data["Name"].startswith("Conversion of document_")
    assert data["Name"].endswith(".pdf")
    new_item = models.Item.objects.get(filename=data["Name"], type=models.ItemTypeChoices.FILE)
    assert new_item.title == new_item.filename == data["Name"]


def test_put_relative_file_relative_target_conflict_in_user_root():
    """RelativeTarget colliding with an existing root item must return 409 even
    when the destination falls back to the user's root."""
    user = factories.UserFactory()
    source = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="source.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.UserItemAccessFactory(item=source, user=user, role=models.RoleChoices.OWNER)
    existing = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        title="report.docx",
        filename="report.docx",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.UserItemAccessFactory(item=existing, user=user, role=models.RoleChoices.OWNER)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(source, user)

    client = APIClient()
    relative = "report.docx".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{source.id}/",
        data=b"converted",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-RelativeTarget": relative,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 409
    assert (
        models.Item.objects.filter(filename="report.docx", type=models.ItemTypeChoices.FILE).count()
        == 1
    )


def test_put_relative_file_relative_target_conflict_with_folder():
    """RelativeTarget colliding with a sibling folder of the same title must return 409."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    source = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FOLDER,
        title="report.docx",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(source, user)

    client = APIClient()
    relative = "report.docx".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{source.id}/",
        data=b"converted",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-RelativeTarget": relative,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 409
    assert not models.Item.objects.filter(
        filename="report.docx", type=models.ItemTypeChoices.FILE
    ).exists()


def test_put_relative_file_relative_target_conflict_root_fallback():
    """RelativeTarget collision must trigger 409 when parent is unwritable and the
    destination falls back to the user's root."""
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    source = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="source.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    user = factories.UserFactory()
    # User has access on source only, NOT on folder → fallback to root.
    factories.UserItemAccessFactory(item=source, user=user, role=models.RoleChoices.EDITOR)
    existing = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        title="report.docx",
        filename="report.docx",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.UserItemAccessFactory(item=existing, user=user, role=models.RoleChoices.OWNER)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(source, user)

    client = APIClient()
    relative = "report.docx".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{source.id}/",
        data=b"converted",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        headers={
            "X-WOPI-Override": "PUT_RELATIVE",
            "X-WOPI-RelativeTarget": relative,
            "X-WOPI-FileConversion": "1",
        },
    )

    assert response.status_code == 409
    assert (
        models.Item.objects.filter(filename="report.docx", type=models.ItemTypeChoices.FILE).count()
        == 1
    )


def test_put_relative_file_suggested_target_keeps_title_filename_consistent():
    """When a sibling folder collides with the suggested name, the new file's
    title and filename are both equal to the disambiguated "Conversion of" name."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    source = factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FILE,
        filename="document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.EDITOR,
    )
    # Sibling folder bearing exactly the suggested target name.
    factories.ItemFactory(
        parent=folder,
        type=models.ItemTypeChoices.FOLDER,
        title="document.pdf",
    )
    user = factories.UserFactory()
    factories.UserItemAccessFactory(item=folder, user=user, role=models.RoleChoices.EDITOR)
    service = AccessUserItemService()
    access_token, _ = service.insert_new_access(source, user)
    default_storage.save(source.file_key, BytesIO(b"original content"))

    client = APIClient()
    suggested = ".pdf".encode("utf-7").decode("ascii")
    response = client.post(
        f"/api/v1.0/wopi/files/{source.id}/",
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
    name = response.json()["Name"]
    new_item = models.Item.objects.get(filename=name, type=models.ItemTypeChoices.FILE)
    assert new_item.title == new_item.filename == name


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
