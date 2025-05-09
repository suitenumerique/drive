"""
Test restoring items after a soft delete via the detail action API endpoint.
"""

from datetime import timedelta

from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_restore_anonymous_user():
    """Anonymous users should not be able to restore deleted items."""
    now = timezone.now() - timedelta(days=15)
    item = factories.ItemFactory(deleted_at=now)

    response = APIClient().post(f"/api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 404
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_found",
                "detail": "Not found.",
            },
        ],
        "type": "client_error",
    }

    item.refresh_from_db()
    assert item.deleted_at == now
    assert item.ancestors_deleted_at == now


@pytest.mark.parametrize("role", [None, "reader", "editor", "administrator"])
def test_api_items_restore_authenticated_no_permission(role):
    """
    Authenticated users who are not owners of a deleted item should
    not be allowed to restore it.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now() - timedelta(days=15)
    item = factories.ItemFactory(
        deleted_at=now, link_reach="public", link_role="editor"
    )
    if role:
        factories.UserItemAccessFactory(item=item, user=user, role=role)

    response = client.post(f"/api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 404
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_found",
                "detail": "Not found.",
            },
        ],
        "type": "client_error",
    }

    item.refresh_from_db()
    assert item.deleted_at == now
    assert item.ancestors_deleted_at == now


def test_api_items_restore_authenticated_owner_success():
    """The owner of a deleted item should be able to restore it."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now() - timedelta(days=15)
    item = factories.ItemFactory(deleted_at=now)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 200
    assert response.json() == {"detail": "item has been successfully restored."}

    item.refresh_from_db()
    assert item.deleted_at is None
    assert item.ancestors_deleted_at is None


def test_api_items_restore_authenticated_owner_not_deleted():
    """An error should be raised when trying to restore an item that is not deleted."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "deleted_at",
                "code": "item_restore_not_deleted",
                "detail": "This item is not deleted.",
            },
        ],
        "type": "validation_error",
    }

    item.refresh_from_db()
    assert item.deleted_at is None
    assert item.ancestors_deleted_at is None


def test_api_items_restore_authenticated_owner_ancestor_deleted():
    """
    The restored item should still be marked as deleted if one of its
    ancestors is soft deleted as well.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    grand_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    item.soft_delete()
    item_deleted_at = item.deleted_at
    assert item_deleted_at is not None

    grand_parent.soft_delete()
    grand_parent_deleted_at = grand_parent.deleted_at
    assert grand_parent_deleted_at is not None

    response = client.post(f"/api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 200
    assert response.json() == {"detail": "item has been successfully restored."}

    item.refresh_from_db()
    assert item.deleted_at is None
    # item is still marked as deleted
    assert item.ancestors_deleted_at == grand_parent_deleted_at
    assert grand_parent_deleted_at > item_deleted_at


def test_api_items_restore_authenticated_owner_expired():
    """It should not be possible to restore an item beyond the allowed time limit."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now() - timedelta(days=40)
    item = factories.ItemFactory(deleted_at=now)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.post(f"/api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 404
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_found",
                "detail": "Not found.",
            },
        ],
        "type": "client_error",
    }
