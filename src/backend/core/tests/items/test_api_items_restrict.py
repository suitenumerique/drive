"""Tests for items API endpoint: restrict / unrestrict actions."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_restrict_owner_can_activate():
    """An owner can activate restriction on a folder."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{folder.id!s}/restrict/")
    assert response.status_code == 200
    assert response.json()["is_restricted"] is True

    folder.refresh_from_db()
    assert folder.is_restricted is True
    assert str(folder.path) == str(folder.id)
    assert folder.shortcut.type == models.ItemTypeChoices.SHORTCUT
    assert models.ItemAccess.objects.filter(item=folder, user=user, role="owner").count() == 1


def test_api_items_restrict_non_owner_cannot_activate():
    """A non-owner cannot activate restriction on a folder."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "administrator")],
    )

    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{folder.id!s}/restrict/")
    assert response.status_code == 403

    folder.refresh_from_db()
    assert folder.is_restricted is False


def test_api_items_restrict_owner_cannot_activate_a_root():
    """A root folder cannot be restricted, even by its owner."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{folder.id!s}/restrict/")
    assert response.status_code == 403

    folder.refresh_from_db()
    assert folder.is_restricted is False


def test_api_items_restrict_owner_can_deactivate():
    """An owner can deactivate restriction on a folder."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{folder.id!s}/restrict/")
    assert response.status_code == 200
    assert response.json()["is_restricted"] is False

    folder.refresh_from_db()
    assert folder.is_restricted is False
    assert str(folder.path) == f"{parent.id!s}.{folder.id!s}"
    assert not models.Item.objects.filter(target=folder).exists()


def test_api_items_restrict_excluded_owner_cannot_deactivate():
    """A user without explicit access cannot deactivate a restricted folder."""
    parent_owner = factories.UserFactory()
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_owner, "owner"), (user, "owner")],
    )
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)

    client = APIClient()
    client.force_login(parent_owner)

    response = client.delete(f"/api/v1.0/items/{folder.id!s}/restrict/")
    assert response.status_code == 403

    folder.refresh_from_db()
    assert folder.is_restricted is True


def test_api_items_restrict_partial_update_ignores_field():
    """The is_restricted field is read only on item update."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    client = APIClient()
    client.force_login(user)

    response = client.patch(
        f"/api/v1.0/items/{folder.id!s}/",
        {"is_restricted": True},
        format="json",
    )
    assert response.status_code == 200

    folder.refresh_from_db()
    assert folder.is_restricted is False


def test_api_items_restrict_response_includes_field():
    """The is_restricted field is present in the API response."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{folder.id!s}/")
    assert response.status_code == 200
    assert "is_restricted" in response.json()
    assert response.json()["is_restricted"] is False
