"""Tests for the items API endpoint creating new files."""

# pylint: disable=missing-function-docstring

from django.core.cache import cache
from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models
from wopi.tasks.configure_wopi import (
    WOPI_CONFIGURATION_CACHE_KEY,
    WOPI_DEFAULT_CONFIGURATION,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _disable_debug_toolbar(settings):
    # The dev docker-compose runs tests with the Development settings, which
    # enables the Django debug toolbar. Disable it for these API tests to avoid
    # staticfiles manifest lookups during response post-processing.
    settings.DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: False}


def test_api_items_new_file_creates_ooxml_placeholder_in_creating_state():
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/new-file/",
        {
            "filename_stem": "Rapport",
            "extension": "docx",
            "kind": "text",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    item = models.Item.objects.get(id=payload["id"])
    assert item.filename == "Rapport.docx"
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert (item.size or 0) > 0
    assert default_storage.exists(item.file_key)


def test_api_items_new_file_creates_ooxml_placeholder_in_creating_state_when_editnew_supported(
    settings,
):
    settings.WOPI_CLIENTS = ["vendorA"]
    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {
            **WOPI_DEFAULT_CONFIGURATION,
            "extensions_editnew": {"docx": "https://vendorA.test/editnew?"},
        },
        timeout=60,
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/new-file/",
        {
            "filename_stem": "Rapport",
            "extension": "docx",
            "kind": "text",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    item = models.Item.objects.get(id=payload["id"])
    assert item.filename == "Rapport.docx"
    assert item.upload_state == models.ItemUploadStateChoices.CREATING
    assert item.size == 0
    assert default_storage.exists(item.file_key)


def test_api_items_new_file_creates_standard_file_ready():
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/new-file/",
        {
            "filename_stem": "README",
            "extension": "md",
            "kind": "text",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    item = models.Item.objects.get(id=payload["id"])
    assert item.filename == "README.md"
    assert item.upload_state == models.ItemUploadStateChoices.READY
    assert item.size == 0
    assert default_storage.exists(item.file_key)


def test_api_items_new_file_applies_collision_to_filename_and_title():
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(user=user, item=parent, role="owner")

    first = client.post(
        "/api/v1.0/items/new-file/",
        {
            "parent_id": str(parent.id),
            "filename_stem": "Rapport",
            "extension": "docx",
            "kind": "text",
        },
        format="json",
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1.0/items/new-file/",
        {
            "parent_id": str(parent.id),
            "filename_stem": "Rapport",
            "extension": "docx",
            "kind": "text",
        },
        format="json",
    )
    assert second.status_code == 201

    item = models.Item.objects.get(id=second.json()["id"])
    assert item.title == "Rapport_01.docx"
    assert item.filename == "Rapport_01.docx"
    assert default_storage.exists(item.file_key)
