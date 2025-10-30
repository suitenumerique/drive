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
    assert response.status_code == 403


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

    assert not models.Item.objects.filter(id=item.id).exists()


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
        "errors": [
            {
                "attr": "hard_deleted_at",
                "code": "item_hard_delete_should_soft_delete_first",
                "detail": "To hard delete an item, it must first be soft deleted.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_hard_delete_authenticated_owner_already_hard_deleted_should_fail():
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


def test_api_items_hard_delete_suspicious_item_should_not_work_for_non_creator():
    """
    Non-creators should not be able to hard delete suspicious items.
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
    suspicious_item.soft_delete()

    response = client.delete(f"/api/v1.0/items/{suspicious_item.id!s}/hard-delete/")
    assert response.status_code == 404


def test_api_items_hard_delete_suspicious_item_should_work_for_creator():
    """
    Creators should be able to hard delete their own suspicious items.
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
    suspicious_item.soft_delete()

    response = client.delete(f"/api/v1.0/items/{suspicious_item.id!s}/hard-delete/")
    assert response.status_code == 204

    assert not models.Item.objects.filter(id=suspicious_item.id).exists()
