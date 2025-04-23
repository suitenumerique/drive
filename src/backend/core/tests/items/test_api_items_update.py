"""
Tests for items API endpoint in drive's core app: update
"""

import random

from django.contrib.auth.models import AnonymousUser

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("via_parent", [True, False])
@pytest.mark.parametrize(
    "reach, role",
    [
        ("restricted", "reader"),
        ("restricted", "editor"),
        ("authenticated", "reader"),
        ("authenticated", "editor"),
        ("public", "reader"),
    ],
)
def test_api_items_update_anonymous_forbidden(reach, role, via_parent):
    """
    Anonymous users should not be allowed to update an item when link
    configuration does not allow it.
    """
    if via_parent:
        grand_parent = factories.ItemFactory(
            link_reach=reach, link_role=role, type=models.ItemTypeChoices.FOLDER
        )
        parent = factories.ItemFactory(
            parent=grand_parent,
            link_reach="restricted",
            type=models.ItemTypeChoices.FOLDER,
        )
        item = factories.ItemFactory(parent=parent, link_reach="restricted")
    else:
        item = factories.ItemFactory(link_reach=reach, link_role=role)

    old_item_values = serializers.ItemSerializer(instance=item).data

    new_item_values = serializers.ItemSerializer(instance=factories.ItemFactory()).data
    response = APIClient().put(
        f"/api/v1.0/items/{item.id!s}/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }

    item.refresh_from_db()
    item_values = serializers.ItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("via_parent", [True, False])
@pytest.mark.parametrize(
    "reach,role",
    [
        ("public", "reader"),
        ("authenticated", "reader"),
        ("restricted", "reader"),
        ("restricted", "editor"),
    ],
)
def test_api_items_update_authenticated_unrelated_forbidden(reach, role, via_parent):
    """
    Authenticated users should not be allowed to update a item to which
    they are not related if the link configuration does not allow it.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    if via_parent:
        grand_parent = factories.ItemFactory(
            link_reach=reach, link_role=role, type=models.ItemTypeChoices.FOLDER
        )
        parent = factories.ItemFactory(
            parent=grand_parent,
            link_reach="restricted",
            type=models.ItemTypeChoices.FOLDER,
        )
        item = factories.ItemFactory(parent=parent, link_reach="restricted")
    else:
        item = factories.ItemFactory(link_reach=reach, link_role=role)

    old_item_values = serializers.ItemSerializer(instance=item).data
    new_item_values = serializers.ItemSerializer(instance=factories.ItemFactory()).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }

    item.refresh_from_db()
    item_values = serializers.ItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize(
    "is_authenticated,reach,role",
    [
        (False, "public", "editor"),
        (True, "public", "editor"),
        (True, "authenticated", "editor"),
    ],
)
def test_api_items_update_anonymous_or_authenticated_unrelated(
    is_authenticated, reach, role
):
    """
    Anonymous and authenticated users should be able to update an item to which
    they are not related if the link configuration allows it.
    """
    client = APIClient()

    if is_authenticated:
        user = factories.UserFactory()
        client.force_login(user)
    else:
        user = AnonymousUser()

    grand_parent = factories.ItemFactory(
        link_reach=reach, link_role=role, type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        link_reach="restricted",
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=parent, link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )

    old_item_values = serializers.ItemSerializer(instance=item).data
    new_item_values = serializers.ItemSerializer(
        instance=factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    ).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 200

    item = models.Item.objects.get(pk=item.pk)
    item_values = serializers.ItemSerializer(instance=item).data
    for key, value in item_values.items():
        if key in [
            "id",
            "accesses",
            "created_at",
            "creator",
            "depth",
            "link_reach",
            "link_role",
            "numchild",
            "path",
            "type",
            "upload_state",
        ]:
            assert value == old_item_values[key]
        elif key == "updated_at":
            assert value > old_item_values[key]
        else:
            assert value == new_item_values[key]


@pytest.mark.parametrize("via_parent", [True, False])
@pytest.mark.parametrize("via", VIA)
def test_api_items_update_authenticated_reader(via, via_parent, mock_user_teams):
    """
    Users who are reader of a item should not be allowed to update it.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    if via_parent:
        grand_parent = factories.ItemFactory(
            link_reach="restricted", type=models.ItemTypeChoices.FOLDER
        )
        parent = factories.ItemFactory(
            parent=grand_parent,
            link_reach="restricted",
            type=models.ItemTypeChoices.FOLDER,
        )
        item = factories.ItemFactory(parent=parent, link_reach="restricted")
        access_item = grand_parent
    else:
        item = factories.ItemFactory(link_reach="restricted")
        access_item = item

    if via == USER:
        factories.UserItemAccessFactory(item=access_item, user=user, role="reader")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=access_item, team="lasuite", role="reader")

    old_item_values = serializers.ItemSerializer(instance=item).data

    new_item_values = serializers.ItemSerializer(instance=factories.ItemFactory()).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }

    item.refresh_from_db()
    item_values = serializers.ItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("via_parent", [True, False])
@pytest.mark.parametrize("role", ["editor", "administrator", "owner"])
@pytest.mark.parametrize("via", VIA)
def test_api_items_update_authenticated_editor_administrator_or_owner(
    via, role, via_parent, mock_user_teams
):
    """
    A user who is administrator or owner of a item should be allowed to update it via parent or not.
    A user who is editor of a item should be allowed to update it only via parent.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    if via_parent:
        grand_parent = factories.ItemFactory(
            link_reach="restricted", type=models.ItemTypeChoices.FOLDER
        )
        parent = factories.ItemFactory(
            parent=grand_parent,
            link_reach="restricted",
            type=models.ItemTypeChoices.FOLDER,
        )
        item = factories.ItemFactory(
            parent=parent, link_reach="restricted", type=models.ItemTypeChoices.FOLDER
        )
        access_item = grand_parent
    else:
        item = factories.ItemFactory(
            link_reach="restricted", type=models.ItemTypeChoices.FOLDER
        )
        access_item = item

    if via == USER:
        factories.UserItemAccessFactory(item=access_item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=access_item, team="lasuite", role=role)

    old_item_values = serializers.ItemSerializer(instance=item).data

    new_item_values = serializers.ItemSerializer(
        instance=factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    ).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/",
        new_item_values,
        format="json",
    )

    if role == "editor" and not via_parent:
        assert response.status_code == 403
        return

    assert response.status_code == 200

    item = models.Item.objects.get(pk=item.pk)
    item_values = serializers.ItemSerializer(instance=item).data
    for key, value in item_values.items():
        if key in [
            "id",
            "created_at",
            "creator",
            "depth",
            "link_reach",
            "link_role",
            "nb_accesses",
            "numchild",
            "path",
            "type",
            "upload_state",
        ]:
            assert value == old_item_values[key]
        elif key == "updated_at":
            assert value > old_item_values[key]
        else:
            assert value == new_item_values[key]


@pytest.mark.parametrize("via", VIA)
def test_api_items_update_administrator_or_owner_of_another(via, mock_user_teams):
    """
    Being administrator or owner of a item should not grant authorization to update
    another item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(
            item=item, user=user, role=random.choice(["administrator", "owner"])
        )
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(
            item=item,
            team="lasuite",
            role=random.choice(["administrator", "owner"]),
        )

    other_item = factories.ItemFactory(title="Old title", link_role="reader")
    old_item_values = serializers.ItemSerializer(instance=other_item).data

    new_item_values = serializers.ItemSerializer(instance=factories.ItemFactory()).data
    response = client.put(
        f"/api/v1.0/items/{other_item.id!s}/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403

    other_item.refresh_from_db()
    other_item_values = serializers.ItemSerializer(instance=other_item).data
    assert other_item_values == old_item_values


def test_api_items_update_title_unique_in_current_path():
    """
    The title of an item should be unique in the current path.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(
        title="item1",
        type=models.ItemTypeChoices.FOLDER,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )
    child = factories.ItemFactory(
        title="child1",
        type=models.ItemTypeChoices.FOLDER,
        parent=root,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    factories.ItemFactory(
        title="child2",
        type=models.ItemTypeChoices.FOLDER,
        parent=root,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    # update child1 to rename it to child2 should fails
    response = client.put(
        f"/api/v1.0/items/{child.id!s}/",
        {"title": "child2"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "title": "An item with this title already exists in the current path."
    }


def test_api_items_update_title_unique_in_current_path_soft_deleted():
    """
    Reusing a title of a soft-deleted item should be allowed.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(
        title="item1",
        type=models.ItemTypeChoices.FOLDER,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )
    child = factories.ItemFactory(
        title="child1",
        type=models.ItemTypeChoices.FOLDER,
        parent=root,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )
    child.soft_delete()

    child2 = factories.ItemFactory(
        title="child2",
        type=models.ItemTypeChoices.FOLDER,
        parent=root,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    # update child 2 title using child 1 title is allowed
    response = client.put(
        f"/api/v1.0/items/{child2.id!s}/",
        {"title": "child1"},
        format="json",
    )
    assert response.status_code == 200


def test_api_items_update_description():
    """
    Test the description of an item can be updated.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        description="Old description",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/",
        {"description": "New description"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["description"] == "New description"

    item.refresh_from_db()
    assert item.description == "New description"


def test_api_items_update_empty_description():
    """
    Empty description should be allowed.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        description="Old description",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
    )

    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/",
        {"description": ""},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["description"] == ""

    item.refresh_from_db()
    assert item.description == ""
