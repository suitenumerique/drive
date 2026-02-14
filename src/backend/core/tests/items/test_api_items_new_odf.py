"""Tests for the items API endpoint creating new ODF documents."""

# pylint: disable=missing-function-docstring

from io import BytesIO
from zipfile import ZipFile

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _disable_debug_toolbar(settings):
    # The dev docker-compose runs tests with the Development settings, which
    # enables the Django debug toolbar. Disable it for these API tests to avoid
    # staticfiles manifest lookups during response post-processing.
    settings.DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: False}


def test_api_items_new_odf_creates_valid_odt_in_folder():
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, link_reach="restricted"
    )
    factories.UserItemAccessFactory(user=user, item=parent, role="owner")

    response = client.post(
        "/api/v1.0/items/new-odf/",
        {
            "parent_id": str(parent.id),
            "filename_stem": "New text document",
            "extension": "odt",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert "policy" not in payload

    item = models.Item.objects.get(id=payload["id"])
    assert item.type == models.ItemTypeChoices.FILE
    assert item.filename == "New text document.odt"
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size and item.size > 0
    assert default_storage.exists(item.file_key)


def test_api_items_new_odf_applies_collision_to_filename_and_title():
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, link_reach="restricted"
    )
    factories.UserItemAccessFactory(user=user, item=parent, role="owner")

    existing = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
        title="New text document.odt",
        filename="New text document.odt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    default_storage.save(existing.file_key, BytesIO(b"content"))

    response = client.post(
        "/api/v1.0/items/new-odf/",
        {
            "parent_id": str(parent.id),
            "filename_stem": "New text document",
            "extension": "odt",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    item = models.Item.objects.get(id=payload["id"])
    assert item.title == "New text document_01.odt"
    assert item.filename == "New text document_01.odt"
    assert default_storage.exists(item.file_key)

    raw = default_storage.open(item.file_key, "rb").read()
    with ZipFile(BytesIO(raw)) as zf:
        assert zf.read("mimetype").decode("utf-8") == (
            "application/vnd.oasis.opendocument.text"
        )
        assert "META-INF/manifest.xml" in set(zf.namelist())


def test_api_items_new_odf_rejects_extension_mismatch():
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/new-odf/",
        {"kind": "odt", "filename": "New text document.ods"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "filename",
                "code": "item_create_file_extension_mismatch",
                "detail": "Filename extension does not match document type.",
            }
        ],
        "type": "validation_error",
    }


def test_api_items_new_odf_anonymous_rejected():
    response = APIClient().post(
        "/api/v1.0/items/new-odf/",
        {"kind": "odt", "filename": "New text document.odt"},
        format="json",
    )

    assert response.status_code == 401
