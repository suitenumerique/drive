"""Test related to item upload ended API."""

import logging
from io import BytesIO
from unittest import mock

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api.viewsets import malware_detection
from core.models import ItemTypeChoices, ItemUploadStateChoices, LinkRoleChoices

pytestmark = pytest.mark.django_db


def test_api_item_upload_ended_anonymous():
    """Anonymous users should not be allowed to end an upload."""
    item = factories.ItemFactory()
    response = APIClient().post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 401


@pytest.mark.parametrize("role", [None, "reader"])
def test_api_item_upload_ended_no_permissions(role):
    """Users without write permissions should not be allowed to end an upload."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    if role:
        item = factories.ItemFactory(
            users=[(user, role)], link_role=LinkRoleChoices.READER
        )
    else:
        item = factories.ItemFactory(link_role=LinkRoleChoices.READER)

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "item_type", [t[0] for t in ItemTypeChoices.choices if t[0] != ItemTypeChoices.FILE]
)
def test_api_item_upload_ended_on_none_file_item(item_type):
    """Users should not be allowed to end an upload on items that are not files."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=item_type)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")
    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "code": "item_upload_type_unavailable",
                "detail": "This action is only available for items of type FILE.",
                "attr": "item",
            }
        ],
    }


def test_api_item_upload_ended_on_wrong_upload_state():
    """
    Users should not be allowed to end an upload on items that are not in the PENDING upload state.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE)
    item.upload_state = ItemUploadStateChoices.READY
    item.save()
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "code": "item_upload_state_not_pending",
                "detail": "This action is only available for items in PENDING state.",
                "attr": "item",
            }
        ],
    }


def test_api_item_upload_ended_success():
    """
    Users should be able to end an upload on items that are files and in the UPLOADING upload state.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE, filename="my_file.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    with (
        mock.patch.object(malware_detection, "analyse_file") as mock_analyse_file,
        mock.patch("core.api.viewsets.mirror_item") as mock_mirror_item,
    ):
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    mock_analyse_file.assert_called_once_with(item.file_key, item_id=item.id)
    mock_mirror_item.assert_called_once_with(item)
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.upload_state == ItemUploadStateChoices.ANALYZING
    assert item.mimetype == "text/plain"
    assert item.size == 8

    assert response.json()["mimetype"] == "text/plain"


def test_api_item_upload_ended_empty_file():
    """Upload an empty file should not raise an error."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE, filename="my_file.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    default_storage.save(item.file_key, BytesIO(b""))

    with (
        mock.patch.object(malware_detection, "analyse_file") as mock_analyse_file,
        mock.patch("core.api.viewsets.mirror_item") as mock_mirror_item,
    ):
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    mock_analyse_file.assert_called_once_with(item.file_key, item_id=item.id)
    mock_mirror_item.assert_called_once_with(item)
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.upload_state == ItemUploadStateChoices.ANALYZING
    assert item.mimetype == "application/x-empty"
    assert item.size == 0

    assert response.json()["mimetype"] == "application/x-empty"


@mock.patch("core.api.viewsets.get_entitlements_backend")
def test_api_item_upload_ended_entitlements_backend_returns_falsy(
    mock_get_entitlements_backend,
):
    """
    Test that the API returns a 403 when the entitlements backend returns a falsy result.
    It should hard delete the item.
    """
    # Mock the entitlement backend to return a falsy result
    mock_entitlement_backend = mock.Mock()
    mock_entitlement_backend.can_upload.return_value = {"result": False}
    mock_get_entitlements_backend.return_value = mock_entitlement_backend

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE, filename="my_file.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 403
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                "code": "permission_denied",
                "detail": "You do not have permission to upload files.",
                "attr": None,
            }
        ],
    }

    assert not models.Item.objects.filter(id=item.id).exists()


@mock.patch("core.api.viewsets.get_entitlements_backend")
def test_api_item_upload_ended_entitlements_backend_returns_falsy_custom_message(
    mock_get_entitlements_backend,
):
    """
    Test that the API returns a 403 when the entitlements backend returns a falsy result
    with a custom message. It should hard delete the item.
    """
    # Mock the entitlement backend to return a falsy result
    mock_entitlement_backend = mock.Mock()
    mock_entitlement_backend.can_upload.return_value = {
        "result": False,
        "message": "Hello World",
    }
    mock_get_entitlements_backend.return_value = mock_entitlement_backend

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE, filename="my_file.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 403
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                "code": "permission_denied",
                "detail": "Hello World",
                "attr": None,
            }
        ],
    }

    assert not models.Item.objects.filter(id=item.id).exists()


def test_api_item_upload_ended_mimetype_not_allowed(settings, caplog):
    """
    Test that the API returns a 400 when the mimetype is not allowed.
    Item should be deleted and the file should be deleted from the storage.
    """
    settings.RESTRICT_UPLOAD_FILE_TYPE = True
    settings.FILE_MIMETYPE_ALLOWED = ["application/pdf"]
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE, filename="my_file.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    with caplog.at_level(logging.INFO):
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    assert response.status_code == 400
    assert (
        "upload_ended: mimetype not allowed text/plain for filename my_file.txt"
        in caplog.text
    )

    assert not models.Item.objects.filter(id=item.id).exists()
    assert not default_storage.exists(item.file_key)


def test_api_item_upload_ended_mimetype_not_allowed_not_checking_mimetype(settings):
    """
    Test that the API returns a 200 when the mimetype is not allowed but not checking the mimetype.
    """
    settings.RESTRICT_UPLOAD_FILE_TYPE = False
    settings.FILE_MIMETYPE_ALLOWED = ["application/pdf"]
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FILE, filename="my_file.txt")
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    default_storage.save(
        item.file_key,
        BytesIO(b"my prose"),
    )

    with mock.patch.object(malware_detection, "analyse_file") as mock_analyse_file:
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")

    mock_analyse_file.assert_called_once_with(item.file_key, item_id=item.id)
    assert response.status_code == 200

    item.refresh_from_db()
    assert item.upload_state == ItemUploadStateChoices.ANALYZING
    assert item.mimetype == "text/plain"
    assert item.size == 8

    assert response.json()["mimetype"] == "text/plain"


def test_api_upload_ended_mismatch_mimetype_with_object_storage(caplog):
    """
    Object on storage should have the same mimetype than the one saved in the
    Item object.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=ItemTypeChoices.FILE,
        filename="my_file.pdf",
        title="my_file.pdf",
        users=[(user, "owner")],
    )

    s3_client = default_storage.connection.meta.client

    s3_client.put_object(
        Bucket=default_storage.bucket_name,
        Key=item.file_key,
        ContentType="text/html",
        Body=BytesIO(
            b'<meta http-equiv="refresh" content="0; url=https://fichiers.numerique.gouv.fr">'
        ),
        Metadata={
            "foo": "bar",
        },
    )

    head_object = s3_client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )

    assert head_object["ContentType"] == "text/html"
    with caplog.at_level(logging.INFO, logger="core.api.viewsets"):
        response = client.post(f"/api/v1.0/items/{item.id!s}/upload-ended/")
    assert (
        "upload_ended: content type mismatch between object storage and item, "
        "updating from text/html to application/pdf" in caplog.text
    )
    assert response.status_code == 200

    item.refresh_from_db()

    assert item.mimetype == "application/pdf"

    head_object = s3_client.head_object(
        Bucket=default_storage.bucket_name, Key=item.file_key
    )
    assert head_object["ContentType"] == "application/pdf"
    assert head_object["Metadata"] == {"foo": "bar"}
