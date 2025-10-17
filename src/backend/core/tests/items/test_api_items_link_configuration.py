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
    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
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
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
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
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
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


def test_api_items_link_configuration_suspicious_item_should_not_work_for_non_creator():
    """
    Non-creators should not be able to update link configuration for suspicious items.
    """
    creator = factories.UserFactory()
    other_user = factories.UserFactory()
    client = APIClient()
    client.force_login(other_user)

    suspicious_item = factories.ItemFactory(
        creator=creator,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[
            (creator, models.RoleChoices.OWNER),
            (other_user, models.RoleChoices.ADMIN),
        ],
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
    )

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data

    response = client.put(
        f"/api/v1.0/items/{suspicious_item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 404


def test_api_items_link_configuration_suspicious_item_should_work_for_creator():
    """
    Creators should be able to update link configuration for their own suspicious items.
    """
    creator = factories.UserFactory()
    client = APIClient()
    client.force_login(creator)

    suspicious_item = factories.ItemFactory(
        creator=creator,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[(creator, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
    )

    new_item_values = serializers.LinkItemSerializer(
        instance=factories.ItemFactory()
    ).data

    response = client.put(
        f"/api/v1.0/items/{suspicious_item.id!s}/link-configuration/",
        new_item_values,
        format="json",
    )
    assert response.status_code == 200

    suspicious_item = models.Item.objects.get(pk=suspicious_item.pk)
    item_values = serializers.LinkItemSerializer(instance=suspicious_item).data
    for key, value in item_values.items():
        assert value == new_item_values[key]
