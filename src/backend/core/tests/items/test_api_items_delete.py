"""
Tests for items API endpoint in drive's core app: delete
"""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_api_items_delete_anonymous():
    """Anonymous users should not be allowed to destroy a item."""
    item = factories.ItemFactory()
    existing_items = models.Item.objects.all().count()

    response = APIClient().delete(
        f"/api/v1.0/items/{item.id!s}/",
    )

    assert response.status_code == 401
    assert models.Item.objects.count() == existing_items


@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
def test_api_items_delete_authenticated_unrelated(reach, role):
    """
    Authenticated users should not be allowed to delete a item to which
    they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=reach, link_role=role)
    existing_items = models.Item.objects.all().count()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/",
    )

    assert response.status_code == 403
    assert models.Item.objects.count() == existing_items


@pytest.mark.parametrize("role", ["reader", "editor", "administrator"])
@pytest.mark.parametrize("via", VIA)
def test_api_items_delete_authenticated_not_owner(via, role, mock_user_teams):
    """
    Authenticated users should not be allowed to delete a item for which they are
    only a reader, editor or administrator.
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

    existing_items = models.Item.objects.all().count()
    response = client.delete(
        f"/api/v1.0/items/{item.id}/",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }
    assert models.Item.objects.count() == existing_items


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_api_items_delete_authenticated_owner_of_ancestor(depth):
    """
    Authenticated users should not be able to delete an item for which
    they are only owner of an ancestor.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    items = []
    for i in range(depth):
        items.append(
            factories.UserItemAccessFactory(
                role="owner",
                user=user,
                item__type=models.ItemTypeChoices.FOLDER,
                item__creator=user,
            ).item
            if i == 0
            else factories.ItemFactory(
                parent=items[-1],
                type=models.ItemTypeChoices.FOLDER,
                creator=user,
            )
        )
    assert models.Item.objects.count() == depth + 1

    response = client.delete(
        f"/api/v1.0/items/{items[-1].id}/",
    )

    assert response.status_code == 204

    # Make sure it is only a soft delete
    assert models.Item.objects.count() == depth + 1
    assert models.Item.objects.filter(deleted_at__isnull=True).count() == depth
    assert models.Item.objects.filter(deleted_at__isnull=False).count() == 1


@pytest.mark.parametrize("via", VIA)
def test_api_items_delete_authenticated_owner(via, mock_user_teams):
    """
    Authenticated users should be able to delete a item they own.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role="owner")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role="owner")

    response = client.delete(
        f"/api/v1.0/items/{item.id}/",
    )

    assert response.status_code == 204

    # Make sure it is only a soft delete
    item.refresh_from_db()
    assert item.deleted_at is not None
