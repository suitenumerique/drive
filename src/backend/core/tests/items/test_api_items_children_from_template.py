"""
Tests for items API endpoint in drive's core app: create children from template
"""

from random import choice
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
        f"/api/v1.0/items/{item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
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
        f"/api/v1.0/items/{item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
        },
    )

    assert response.status_code == 403
    assert Item.objects.count() == items_created


def test_api_items_children_from_template_authenticated_reader_forbidden():
    """
    Authenticated users with read-only access should not be allowed
    to create items from template.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted", type=ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(user=user, item=item, role="reader")

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
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
        f"/api/v1.0/items/{item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
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
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": extension,
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
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "docx",
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


def test_api_items_children_from_template_missing_extension():
    """
    Creating an item from template without an extension should fail.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "extension",
                "code": "required",
                "detail": "This field is required.",
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
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "extension": "odt",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "attr": "title",
                "code": "required",
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
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "",
            "extension": "odt",
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


def test_api_items_children_from_template_not_a_folder():
    """
    It should not be possible to create an item from template below an item
    of type other than folder.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user,
        role="owner",
        item__type=choice(
            [type for type in ItemTypeChoices.values if type != ItemTypeChoices.FOLDER]
        ),
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
        },
    )

    assert response.status_code == 400
    assert Item.objects.count() == items_created
    assert response.json() == {
        "errors": [
            {
                "attr": "type",
                "code": "item_create_child_type_folder_only",
                "detail": "Only folders can have children.",
            },
        ],
        "type": "validation_error",
    }


@pytest.mark.parametrize("message", [None, "Hello World"])
@mock.patch("core.api.viewsets.get_entitlements_backend")
def test_api_items_children_from_template_entitlements_forbidden(
    mock_get_entitlements_backend, message
):
    """
    Test that the API returns a 403 when the entitlements backend returns a falsy result.
    """
    mock_entitlement_backend = mock.Mock()
    return_value = {"result": False}
    if message:
        return_value["message"] = message
    mock_entitlement_backend.can_upload.return_value = return_value
    mock_get_entitlements_backend.return_value = mock_entitlement_backend

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    items_created = Item.objects.count()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
        },
    )

    assert response.status_code == 403
    assert Item.objects.count() == items_created
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                "code": "permission_denied",
                "detail": message or "You do not have permission to upload files.",
                "attr": None,
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
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
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
    factories.ItemFactory(
        parent=access.item, title="my document", type=ItemTypeChoices.FILE
    )

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "my document_01"


def test_api_items_children_from_template_link_reach_restricted():
    """
    Items created from template should have restricted link reach by default.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=ItemTypeChoices.FOLDER
    )

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.link_reach == "restricted"


@pytest.mark.parametrize(
    "extension,expected_mimetype",
    [
        ("odt", "application/vnd.oasis.opendocument.text"),
        ("ods", "application/vnd.oasis.opendocument.spreadsheet"),
        ("odp", "application/vnd.oasis.opendocument.presentation"),
    ],
)
def test_api_items_children_from_template_correct_mimetype(
    extension, expected_mimetype
):
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
        f"/api/v1.0/items/{access.item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": extension,
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.mimetype == expected_mimetype


@pytest.mark.parametrize(
    "reach,role",
    [
        ["public", "editor"],
        ["authenticated", "editor"],
    ],
)
def test_api_items_children_from_template_link_access_success(reach, role):
    """
    Authenticated users with write access via link should be able
    to create items from template.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach=reach, link_role=role, type=ItemTypeChoices.FOLDER
    )

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/from-template/",
        {
            "title": "my document",
            "extension": "odt",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.title == "my document"
    assert child.parent() == item
