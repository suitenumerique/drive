"""Test the item hard delete endpoint."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_hard_delete_anonymous():
    """
    Anonymous users should not be allowed to hard delete an item.
    """
    item = factories.ItemFactory()
    response = APIClient().delete(f"/api/v1.0/items/{item.id!s}/hard-delete/")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "role",
    [
        role
        for role in models.RoleChoices.values
        if role not in models.RoleChoices.OWNER
    ],
)
def test_api_items_hard_delete_authenticated_not_owner(role):
    """
    Authenticated users should not be allowed to hard delete an item if they are not the owner.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory()
    item.soft_delete()
    factories.UserItemAccessFactory(item=item, user=user, role=role)

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{item.id!s}/hard-delete/")
    assert response.status_code == 404


def test_api_items_hard_delete_authenticated_owner():
    """
    Authenticated users should be allowed to hard delete an item if they are the owner.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)
    item.soft_delete()

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{item.id!s}/hard-delete/")
    assert response.status_code == 204

    item.refresh_from_db()
    assert item.hard_deleted_at is not None


def test_api_items_hard_delete_authenticated_owner_not_soft_deleted_should_fails():
    """
    Authenticated users should not be allowed to hard delete an item if it is not soft deleted.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{item.id!s}/hard-delete/")
    assert response.status_code == 400
    assert response.json() == {
        "hard_deleted_at": ["To hard delete an item, it must first be soft deleted."]
    }


def test_api_items_hard_delete_authenticated_owner_already_hard_deleted_should_fails():
    """
    Authenticated users should not be allowed to hard delete an item if it is already hard deleted.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory()
    item.soft_delete()
    item.hard_delete()

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{item.id!s}/hard-delete/")
    assert response.status_code == 404
