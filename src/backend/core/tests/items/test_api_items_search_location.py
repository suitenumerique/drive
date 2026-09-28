"""Tests for the Item viewset search method location filter."""

import datetime

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_search_authenticated_by_location_my_files():
    """Searching with location=my_files should only return items created by the user."""
    user = factories.UserFactory()
    other = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    workspace = factories.ItemFactory(
        title="Workspace",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="My file",
        parent=workspace,
        creator=user,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        title="Shared file",
        parent=workspace,
        creator=other,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    response = client.get("/api/v1.0/items/search/?location=my_files")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {
        "Workspace",
        "My file",
    }

    # location composes with an explicit scope.
    response = client.get("/api/v1.0/items/search/?location=my_files&scope=all")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {
        "Workspace",
        "My file",
    }


def test_api_items_search_authenticated_by_location_shared_with_me():
    """Searching with location=shared_with_me should exclude items created by the user."""
    user = factories.UserFactory()
    other = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    workspace = factories.ItemFactory(
        title="Workspace",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="My file",
        parent=workspace,
        creator=user,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        title="Shared file",
        parent=workspace,
        creator=other,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    response = client.get("/api/v1.0/items/search/?location=shared_with_me")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {"Shared file"}


def test_api_items_search_authenticated_by_location_starred():
    """Searching with location=starred should only return the user's favorite items."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    workspace = factories.ItemFactory(
        title="Workspace",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    favorite = factories.ItemFactory(
        title="Favorite file",
        parent=workspace,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        title="Plain file",
        parent=workspace,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    models.ItemFavorite.objects.create(user=user, item=favorite)

    response = client.get("/api/v1.0/items/search/?location=starred")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {"Favorite file"}


def test_api_items_search_authenticated_by_location_trashbin():
    """Searching with location=trashbin should return the deleted subtree the user owns."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    workspace = factories.ItemFactory(
        title="Workspace",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    deleted_folder = factories.ItemFactory(
        title="folder A",
        parent=workspace,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="folder A child",
        parent=deleted_folder,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    factories.ItemFactory(
        title="folder B",
        parent=workspace,
        type=models.ItemTypeChoices.FOLDER,
    )
    deleted_folder.soft_delete()

    # trashbin returns the deleted root and its descendants without an explicit scope.
    response = client.get("/api/v1.0/items/search/?location=trashbin")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {
        "folder A",
        "folder A child",
    }

    # trashbin overrides the default not_deleted scope even when passed explicitly.
    response = client.get("/api/v1.0/items/search/?location=trashbin&scope=not_deleted")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {
        "folder A",
        "folder A child",
    }


def test_api_items_search_authenticated_by_location_trashbin_requires_owner():
    """Searching with location=trashbin should hide deleted items the user does not own."""
    user = factories.UserFactory()
    other = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    owned = factories.ItemFactory(
        title="Owned workspace",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    owned_deleted = factories.ItemFactory(
        title="Owned deleted",
        parent=owned,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    owned_deleted.soft_delete()

    shared = factories.ItemFactory(
        title="Shared workspace",
        creator=other,
        users=[(user, models.RoleChoices.READER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    reader_deleted = factories.ItemFactory(
        title="Reader deleted",
        parent=shared,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    reader_deleted.soft_delete()

    response = client.get("/api/v1.0/items/search/?location=trashbin")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {"Owned deleted"}


def test_api_items_search_authenticated_by_location_trashbin_excludes_beyond_cutoff():
    """Searching with location=trashbin should exclude items deleted past the cutoff."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    workspace = factories.ItemFactory(
        title="Workspace",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    recent = factories.ItemFactory(
        title="Recent",
        parent=workspace,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    old = factories.ItemFactory(
        title="Old",
        parent=workspace,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    recent.soft_delete()
    old.soft_delete()
    past_cutoff = models.get_trashbin_cutoff() - datetime.timedelta(days=1)
    models.Item.objects.filter(pk=old.pk).update(
        deleted_at=past_cutoff, ancestors_deleted_at=past_cutoff
    )

    response = client.get("/api/v1.0/items/search/?location=trashbin")
    assert response.status_code == 200
    assert {item["title"] for item in response.data["results"]} == {"Recent"}


def test_api_items_search_authenticated_by_location_invalid():
    """An invalid location value should return a 400 error."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory(
        title="Workspace",
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    response = client.get("/api/v1.0/items/search/?location=invalid")
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "location",
                "code": "invalid",
                "detail": "Select a valid choice. invalid is not one of the available choices.",
            },
        ],
        "type": "validation_error",
    }
