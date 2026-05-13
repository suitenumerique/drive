"""
Tests for items API endpoint in drive's core app: create children from template
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories
from core.models import Item, ItemTypeChoices, ItemUploadStateChoices

pytestmark = pytest.mark.django_db


def test_api_items_children_from_template_anonymous():
    """Anonymous users should not be allowed to create items from template."""
    item = factories.ItemFactory(type=ItemTypeChoices.FOLDER)

    items_created = Item.objects.count()

    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 401
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
                "attr": None,
            }
        ],
    }


def test_api_items_children_from_template_authenticated_forbidden():
    """
    Authenticated users with no access on an item should not be allowed
    to create items from template.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted", type=ItemTypeChoices.FOLDER)

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 403
    assert Item.objects.count() == items_created


@pytest.mark.parametrize("role", ["editor", "administrator", "owner"])
def test_api_items_children_from_template_authenticated_success(role):
    """
    Authenticated users with write access on an item should be able
    to create items from template.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted", type=ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(user=user, item=item, role=role)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.title == "my document"
    assert child.filename == "my document.odt"
    assert child.type == ItemTypeChoices.FILE
    assert child.parent() == item
    assert child.creator == user
    assert child.upload_state == ItemUploadStateChoices.READY
    assert child.size > 0
    assert child.mimetype is not None


@pytest.mark.parametrize("extension", ["odt", "ods", "odp"])
def test_api_items_children_from_template_valid_extensions(extension):
    """
    It should be possible to create items from template with all valid extensions.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my document",
            "extension": extension,
            "type": "file",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.title == "my document"
    assert child.filename == f"my document.{extension}"
    assert child.upload_state == ItemUploadStateChoices.READY


def test_api_items_children_from_template_invalid_extension():
    """
    Creating an item from template with an invalid extension should fail.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my document",
            "extension": "docx",
            "type": "file",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "extension",
                "code": "invalid_choice",
                "detail": '"docx" is not a valid choice.',
            }
        ],
    }


def test_api_items_children_from_template_missing_title():
    """
    Creating an item from template without a title should fail.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "title",
                "code": "invalid",
                "detail": "This field is required.",
            }
        ],
    }


def test_api_items_children_from_template_empty_title():
    """
    Creating an item from template with an empty title should fail.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "title",
                "code": "blank",
                "detail": "This field may not be blank.",
            }
        ],
    }


@mock.patch("core.api.viewsets.default_storage")
def test_api_items_children_from_template_storage_error(mock_storage):
    """
    Test that storage errors are handled properly and the item is cleaned up.
    """
    mock_storage.save.side_effect = Exception("Storage unavailable")

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "detail",
                "code": "storage_upload_error",
                "detail": "Error uploading file to storage.",
            }
        ],
    }


def test_api_items_children_from_template_title_already_existing():
    """
    Creating an item from template with a title that already exists at the same level
    should automatically add a number to the title.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(parent=access.item, title="my document", type=ItemTypeChoices.FILE)

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my document",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "my document_01"


@pytest.mark.parametrize(
    "extension,expected_mimetype",
    [
        ("odt", "application/vnd.oasis.opendocument.text"),
        ("ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("odp", "application/vnd.oasis.opendocument.presentation"),
    ],
)
def test_api_items_children_from_template_correct_mimetype(extension, expected_mimetype):
    """
    Items created from template should have the correct MIME type set.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my document",
            "extension": extension,
            "type": "file",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.mimetype == expected_mimetype


def test_api_items_children_from_template_title_with_slash_is_sanitized():
    """
    Creating a file from template with a slash in the title should
    produce a sanitized filename (no slash in the stored filename).
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "30/03/30 - liste à faire",
            "extension": "odt",
            "type": "file",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.filename == "30-03-30 - liste à faire.odt"
