"""Tests for the /items/<id>/convert/ endpoint."""

from unittest import mock

import pytest
from kombu.exceptions import KombuError
from rest_framework.test import APIClient

from core import factories, models
from wopi.conversion.exceptions import ConversionProviderError

pytestmark = pytest.mark.django_db


def _build_user_and_item():
    """Build an EDITOR user with a legacy .doc item ready for conversion."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=parent,
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FILE,
        filename="document.doc",
        mimetype="application/msword",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    return user, item


@pytest.fixture(autouse=True)
def _wopi_settings(settings):
    """Configure the OnlyOffice WOPI client for the conversion tests."""
    settings.WOPI_SRC_BASE_URL = "https://drive.example"
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = "test-jwt-secret"
    settings.WOPI_CLIENTS_CONFIGURATION = {
        "onlyoffice": {
            "options": {
                "ForceConvertExtensions": ["doc"],
                "ConvertServiceUrl": "http://onlyoffice/converter",
            },
        }
    }


def test_convert_endpoint_creates_placeholder_and_queues_task():
    """Return the placeholder and enqueue the conversion task on POST /convert."""
    user, item = _build_user_and_item()
    client = APIClient()
    client.force_login(user)

    with mock.patch("core.api.viewsets.convert_file.delay") as delay_mock:
        response = client.post(f"/api/v1.0/items/{item.id}/convert/")

    assert response.status_code == 201
    body = response.json()
    placeholder = models.Item.objects.get(id=body["id"])
    assert placeholder.upload_state == models.ItemUploadStateChoices.CONVERTING
    assert placeholder.filename == "document (converted).docx"
    assert placeholder.parent().id == item.parent().id
    delay_mock.assert_called_once_with(
        source_item_id=str(item.id),
        converted_item_id=str(placeholder.id),
        user_id=str(user.id),
    )


def test_convert_endpoint_cleans_up_placeholder_when_queueing_fails():
    """Remove the placeholder and let the broker error bubble up."""
    user, item = _build_user_and_item()
    client = APIClient(raise_request_exception=False)
    client.force_login(user)

    with mock.patch("core.api.viewsets.convert_file.delay", side_effect=KombuError):
        response = client.post(f"/api/v1.0/items/{item.id}/convert/")

    assert response.status_code == 500
    assert not models.Item.objects.filter(
        upload_state=models.ItemUploadStateChoices.CONVERTING
    ).exists()


def test_convert_endpoint_returns_403_when_user_cannot_update_item():
    """Return 403 and skip placeholder creation when the user cannot update."""
    _, item = _build_user_and_item()
    other_user = factories.UserFactory()
    client = APIClient()
    client.force_login(other_user)

    with mock.patch("core.api.viewsets.convert_file.delay") as delay_mock:
        response = client.post(f"/api/v1.0/items/{item.id}/convert/")

    assert response.status_code == 403
    assert not models.Item.objects.filter(
        upload_state=models.ItemUploadStateChoices.CONVERTING
    ).exists()
    delay_mock.assert_not_called()


def test_convert_endpoint_retries_perform_conversion_before_deleting_placeholder():
    """Retry up to max_retries on provider errors, then delete the placeholder."""
    user, item = _build_user_and_item()
    client = APIClient(raise_request_exception=False)
    client.force_login(user)

    with mock.patch(
        "wopi.tasks.conversion.perform_conversion",
        side_effect=ConversionProviderError("transient"),
    ) as perform_mock:
        client.post(f"/api/v1.0/items/{item.id}/convert/")

    # 1 initial attempt + 3 retries == 4
    assert perform_mock.call_count == 4
    assert not models.Item.objects.filter(
        upload_state=models.ItemUploadStateChoices.CONVERTING
    ).exists()


def test_convert_endpoint_returns_403_for_unsupported_extension():
    """Reject conversion with 403 for non-legacy file extensions."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        users=[(user, models.RoleChoices.EDITOR)],
        type=models.ItemTypeChoices.FILE,
        filename="image.png",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    client = APIClient()
    client.force_login(user)

    with mock.patch("core.api.viewsets.convert_file.delay") as delay_mock:
        response = client.post(f"/api/v1.0/items/{item.id}/convert/")

    assert response.status_code == 403
    delay_mock.assert_not_called()
