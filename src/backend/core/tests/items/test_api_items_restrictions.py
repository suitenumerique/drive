"""Tests for the restriction target details in the items API."""

from django.db import connection
from django.test.utils import CaptureQueriesContext

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def _create_restricted_folder(parent, user):
    """Create a folder under parent and restrict it as user."""
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=folder, user=user, role="owner")
    return folder.restrict(user)


def test_api_items_restrictions_children_list_exposes_target():
    """The children listing exposes the restriction target, greyed for excluded users."""
    parent_owner = factories.UserFactory()
    owner = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_owner, "owner")],
    )
    folder = _create_restricted_folder(parent, owner)
    restriction = folder.restriction

    client = APIClient()
    client.force_login(parent_owner)

    response = client.get(f"/api/v1.0/items/{parent.id!s}/children/")

    assert response.status_code == 200
    results = {result["id"]: result for result in response.json()["results"]}
    payload = results[str(restriction.id)]
    assert payload["type"] == "restriction"
    assert payload["target"] == {
        "id": str(folder.id),
        "title": folder.title,
        "is_restricted": True,
        "deleted": False,
        "can_access": False,
    }


def test_api_items_restrictions_children_list_target_accessible():
    """The target is accessible for a user holding an explicit access on it."""
    user = factories.UserFactory()
    owner = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "reader")],
    )
    folder = _create_restricted_folder(parent, owner)
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{parent.id!s}/children/")

    assert response.status_code == 200
    results = {result["id"]: result for result in response.json()["results"]}
    assert results[str(folder.restriction.id)]["target"]["can_access"] is True


def test_api_items_restrictions_children_list_target_accessible_via_link():
    """A public link reach on the target grants access through the restriction."""
    parent_owner = factories.UserFactory()
    owner = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_owner, "owner")],
    )
    folder = _create_restricted_folder(parent, owner)
    models.Item.objects.filter(pk=folder.pk).update(link_reach="public")

    client = APIClient()
    client.force_login(parent_owner)

    response = client.get(f"/api/v1.0/items/{parent.id!s}/children/")

    assert response.status_code == 200
    results = {result["id"]: result for result in response.json()["results"]}
    assert results[str(folder.restriction.id)]["target"]["can_access"] is True


def test_api_items_restrictions_retrieve_exposes_target():
    """Retrieving a restriction exposes its target."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, user)
    restriction = folder.restriction

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{restriction.id!s}/")

    assert response.status_code == 200
    assert response.json()["target"]["id"] == str(folder.id)


def test_api_items_restrictions_non_restriction_target_is_none():
    """Regular items expose a null target."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{folder.id!s}/")

    assert response.status_code == 200
    assert response.json()["target"] is None


def test_api_items_restrictions_delete_detaches_the_target():
    """Deleting a restriction detaches the restricted folder without touching it."""
    parent_owner = factories.UserFactory()
    owner = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_owner, "owner")],
    )
    folder = _create_restricted_folder(parent, owner)
    restriction = folder.restriction

    client = APIClient()
    client.force_login(parent_owner)

    response = client.delete(f"/api/v1.0/items/{restriction.id!s}/")

    assert response.status_code == 204
    assert not models.Item.objects.filter(pk=restriction.pk).exists()
    folder.refresh_from_db()
    assert folder.is_restricted is False
    assert folder.deleted_at is None
    assert models.ItemAccess.objects.filter(item=folder, user=owner, role="owner").exists()


def test_api_items_restrictions_delete_forbidden_for_reader():
    """A reader of the containing folder cannot detach a restriction."""
    reader = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(reader, "reader")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    restriction = folder.restriction

    client = APIClient()
    client.force_login(reader)

    response = client.delete(f"/api/v1.0/items/{restriction.id!s}/")

    assert response.status_code == 403
    assert models.Item.objects.filter(pk=restriction.pk).exists()


def test_api_items_restrictions_children_list_constant_queries():
    """The number of queries does not grow with the number of restrictions listed."""
    parent_owner = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_owner, "owner")],
    )
    _create_restricted_folder(parent, factories.UserFactory())

    client = APIClient()
    client.force_login(parent_owner)

    # Warm the nb_accesses cache so both measures run in the same conditions
    client.get(f"/api/v1.0/items/{parent.id!s}/children/")

    with CaptureQueriesContext(connection) as single:
        response = client.get(f"/api/v1.0/items/{parent.id!s}/children/")
        assert response.status_code == 200

    for _ in range(3):
        _create_restricted_folder(parent, factories.UserFactory())

    with CaptureQueriesContext(connection) as many:
        response = client.get(f"/api/v1.0/items/{parent.id!s}/children/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 4

    assert len(many) == len(single)


def test_api_items_restrictions_tree_includes_restrictions():
    """The tree endpoint includes restriction entries so excluded users see them."""
    parent_owner = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_owner, "owner")],
    )
    sibling = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = _create_restricted_folder(parent, factories.UserFactory())
    restriction = folder.restriction

    client = APIClient()
    client.force_login(parent_owner)

    response = client.get(f"/api/v1.0/items/{sibling.id!s}/tree/")

    assert response.status_code == 200
    tree = response.json()
    children_ids = {child["id"] for child in tree["children"]}
    assert str(restriction.id) in children_ids
