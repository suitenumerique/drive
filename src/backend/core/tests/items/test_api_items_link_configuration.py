"""Tests for link configuration of items on API endpoint"""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_link_configuration_update_anonymous(reach, role):
    """Anonymous users should not be allowed to update a link configuration."""
    item = factories.ItemFactory(link_reach=reach, link_role=role)
    old_item_values = serializers.LinkItemSerializer(instance=item).data

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data
    response = APIClient().put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }

    item.refresh_from_db()
    item_values = serializers.LinkItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_link_configuration_update_authenticated_unrelated(reach, role):
    """
    Authenticated users should not be allowed to update the link configuration for
    a item to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=reach, link_role=role)
    old_item_values = serializers.LinkItemSerializer(instance=item).data

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }

    item.refresh_from_db()
    item_values = serializers.LinkItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("role", ["editor", "reader"])
@pytest.mark.parametrize("via", VIA)
def test_api_items_link_configuration_update_authenticated_related_forbidden(
    via, role, mock_user_teams
):
    """
    Users who are readers or editors of a item should not be allowed to update
    the link configuration.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    old_item_values = serializers.LinkItemSerializer(instance=item).data

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }

    item.refresh_from_db()
    item_values = serializers.LinkItemSerializer(instance=item).data
    assert item_values == old_item_values


@pytest.mark.parametrize("role", ["administrator", "owner"])
@pytest.mark.parametrize("via", VIA)
def test_api_items_link_configuration_update_authenticated_related_success(
    via,
    role,
    mock_user_teams,
):
    """
    A user who is administrator or owner of a item should be allowed to update
    the link configuration.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 200

    item = models.Item.objects.get(pk=item.pk)
    item_values = serializers.LinkItemSerializer(instance=item).data
    for key, value in item_values.items():
        assert value == new_item_values[key]
