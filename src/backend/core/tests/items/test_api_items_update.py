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


@pytest.mark.parametrize("via_parent", [True, False])
@pytest.mark.parametrize(
    "is_authenticated,reach,role",
    [
        (False, "public", "editor"),
        (True, "public", "editor"),
        (True, "authenticated", "editor"),
    ],
)
def test_api_items_update_anonymous_or_authenticated_unrelated(
    is_authenticated, reach, role, via_parent
):
    """
    Anonymous and authenticated users should be able to update a item to which
    they are not related if the link configuration allows it.
    """
    client = APIClient()

    if is_authenticated:
        user = factories.UserFactory()
        client.force_login(user)
    else:
        user = AnonymousUser()

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
    """A user who is editor, administrator or owner of a item should be allowed to update it."""
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
        factories.UserItemAccessFactory(item=access_item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=access_item, team="lasuite", role=role)

    old_item_values = serializers.ItemSerializer(instance=item).data

    new_item_values = serializers.ItemSerializer(instance=factories.ItemFactory()).data
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
