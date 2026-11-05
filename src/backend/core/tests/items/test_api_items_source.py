"""
Tests for the `source` field recording the provenance of items.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_item_factory_default_source_is_none():
    """Items without known provenance (e.g. pre-existing data) keep source null."""
    item = factories.ItemFactory()
    assert item.source is None


def test_api_items_create_folder_source_upload():
    """Folders created through the regular API are tagged drive_upload."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {"title": "my folder", "type": models.ItemTypeChoices.FOLDER},
        format="json",
    )

    assert response.status_code == 201
    assert models.Item.objects.get().source == models.ItemSourceChoices.UPLOAD


def test_api_items_create_file_source_upload():
    """Files created through the regular API are tagged drive_upload."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        format="json",
    )

    assert response.status_code == 201
    item = models.Item.objects.get()
    assert item.source == models.ItemSourceChoices.UPLOAD


def test_api_items_children_create_file_source_upload():
    """Files created as children are tagged drive_upload."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = client.post(
        f"/api/v1.0/items/{parent.id!s}/children/",
        {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        format="json",
    )

    assert response.status_code == 201
    child = models.Item.objects.get(id=response.json()["id"])
    assert child.source == models.ItemSourceChoices.UPLOAD


def test_api_items_children_from_template_source_template():
    """Files created from a template are tagged drive_template."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    parent = factories.ItemFactory(
        link_reach="restricted",
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = client.post(
        f"/api/v1.0/items/{parent.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 201
    child = models.Item.objects.get(id=response.json()["id"])
    assert child.source == models.ItemSourceChoices.TEMPLATE


def test_api_items_duplicate_source_duplicate():
    """Duplicated files are tagged drive_duplicate."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="text/plain",
        filename="myfile.txt",
        users=[(user, models.RoleChoices.OWNER)],
    )

    with mock.patch("core.tasks.item.duplicate_file.delay"):
        response = client.post(f"/api/v1.0/items/{item.id!s}/duplicate/")

    assert response.status_code == 201
    duplicated_item = models.Item.objects.get(id=response.json()["id"])
    assert duplicated_item.source == models.ItemSourceChoices.DUPLICATE


@pytest.fixture
def wopi_settings(settings):
    """Configure the OnlyOffice WOPI client for the conversion test."""
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


@pytest.mark.usefixtures("wopi_settings")
def test_api_items_convert_source_convert():
    """Conversion placeholders are tagged drive_convert."""
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
    client = APIClient()
    client.force_login(user)

    with mock.patch("core.api.viewsets.convert_file.delay"):
        response = client.post(f"/api/v1.0/items/{item.id}/convert/")

    assert response.status_code == 201
    placeholder = models.Item.objects.get(id=response.json()["id"])
    assert placeholder.source == models.ItemSourceChoices.CONVERT
