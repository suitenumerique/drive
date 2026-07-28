"""Tests for restricted roots visibility in the items list API endpoint."""

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


def _listed_ids(client):
    """Return the ids listed on the user's root listing."""
    response = client.get("/api/v1.0/items/")
    assert response.status_code == 200
    return {result["id"] for result in response.json()["results"]}


def test_api_items_list_restricted_hidden_when_shortcut_reachable():
    """A member reaching the live shortcut does not see the restricted root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    listed = _listed_ids(client)
    assert str(parent.id) in listed
    assert str(folder.id) not in listed


def test_api_items_list_restricted_visible_without_container_access():
    """A member without access to the container sees the restricted root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    listed = _listed_ids(client)
    assert str(folder.id) in listed
    assert str(parent.id) not in listed


def test_api_items_list_restricted_hidden_via_team_access(mock_user_teams):
    """A team access on the container hides the restricted root."""
    user = factories.UserFactory()
    mock_user_teams.return_value = ["lasuite"]
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.TeamItemAccessFactory(item=parent, team="lasuite", role="reader")
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    assert str(folder.id) not in _listed_ids(client)


def test_api_items_list_restricted_follows_moved_shortcut():
    """Moving the shortcut out of reach makes the restricted root visible again."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")
    other = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder.shortcut.move(other)

    client = APIClient()
    client.force_login(user)

    assert str(folder.id) in _listed_ids(client)


def test_api_items_list_restricted_visible_when_shortcut_deleted():
    """Without a live shortcut the restricted root shows up for its members."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")
    models.Item.objects.filter(target=folder).delete()

    client = APIClient()
    client.force_login(user)

    assert str(folder.id) in _listed_ids(client)


def test_api_items_list_restricted_visible_when_shortcut_trashed():
    """A shortcut under a soft deleted ancestor does not hide the restricted root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")
    parent.soft_delete()

    client = APIClient()
    client.force_login(user)

    assert str(folder.id) in _listed_ids(client)


def test_api_items_list_restricted_hidden_again_after_restore():
    """Restoring the trashed container hides the restricted root again."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")
    parent.soft_delete()
    parent.restore()

    client = APIClient()
    client.force_login(user)

    listed = _listed_ids(client)
    assert str(parent.id) in listed
    assert str(folder.id) not in listed


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_list_restricted_hidden_via_link_on_container(reach):
    """An open link on the container makes the shortcut reachable and hides the root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=reach,
        link_role="reader",
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    assert str(folder.id) not in _listed_ids(client)


def test_api_items_list_restricted_hidden_via_inherited_link():
    """A link inherited from a grandparent counts to reach the shortcut."""
    user = factories.UserFactory()
    grandparent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach="public",
        link_role="reader",
    )
    parent = factories.ItemFactory(
        parent=grandparent,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=None,
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    assert str(folder.id) not in _listed_ids(client)


def test_api_items_list_restricted_constant_queries():
    """The number of queries does not grow with the number of hidden restricted roots."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    client = APIClient()
    client.force_login(user)

    # Warm the nb_accesses cache so both measures run in the same conditions
    client.get("/api/v1.0/items/")

    with CaptureQueriesContext(connection) as single:
        response = client.get("/api/v1.0/items/")
        assert response.status_code == 200

    for _ in range(3):
        other = _create_restricted_folder(parent, factories.UserFactory())
        factories.UserItemAccessFactory(item=other, user=user, role="reader")

    with CaptureQueriesContext(connection) as many:
        response = client.get("/api/v1.0/items/")
        assert response.status_code == 200
        assert [result["id"] for result in response.json()["results"]] == [str(parent.id)]

    assert len(many) == len(single)


def test_api_items_list_restricted_differs_per_user():
    """The same restricted root is hidden or visible depending on the user."""
    insider = factories.UserFactory()
    outsider = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(insider, "owner")],
    )
    folder = _create_restricted_folder(parent, factories.UserFactory())
    factories.UserItemAccessFactory(item=folder, user=insider, role="reader")
    factories.UserItemAccessFactory(item=folder, user=outsider, role="reader")

    insider_client = APIClient()
    insider_client.force_login(insider)
    outsider_client = APIClient()
    outsider_client.force_login(outsider)

    assert str(folder.id) not in _listed_ids(insider_client)
    assert str(folder.id) in _listed_ids(outsider_client)
