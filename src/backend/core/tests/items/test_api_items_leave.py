"""Test leave item API endpoint for users in drive's core app."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_leave_anonymous():
    """Anonymous users cannot leave an item."""
    item = factories.ItemFactory(link_reach="authenticated")

    response = APIClient().post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 401


def test_api_items_leave_no_access():
    """Authenticated users with no access on a restricted item get a 403."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="restricted")
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 403


@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_items_leave_privileged_role_forbidden(role):
    """Owners and administrators cannot leave an item they manage."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, role)])
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 403
    assert models.ItemAccess.objects.filter(item=item, user=user).exists()


@pytest.mark.parametrize("role", ["editor", "reader"])
def test_api_items_leave_with_explicit_access(role):
    """Editors and readers can leave an item, removing their access record."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, role)])
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 204
    assert models.ItemAccess.objects.filter(item=item, user=user).exists() is False


def test_api_items_leave_with_link_trace_only():
    """A user with only a link trace (no explicit access) can leave."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="authenticated", link_traces=[user])
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 204
    assert models.LinkTrace.objects.filter(item=item, user=user).exists() is False


def test_api_items_leave_deleted_item():
    """Soft-deleted items are not found, so leave returns 404."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "editor")])
    item.soft_delete()
    item.refresh_from_db()
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 404
    assert models.ItemAccess.objects.filter(item=item, user=user).exists()


def test_api_items_leave_removes_access_on_subtree():
    """Leaving a parent item also removes the user's access on all descendant items."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(users=[(user, "editor")], type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(
        parent=parent, users=[(user, "editor")], type=models.ItemTypeChoices.FOLDER
    )
    grandchild = factories.ItemFactory(parent=child)
    # Another user's access should be untouched
    other_user = factories.UserFactory()
    other_access = models.ItemAccess.objects.create(item=child, user=other_user)

    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{parent.id!s}/leave/")

    assert response.status_code == 204
    assert models.ItemAccess.objects.filter(user=user).exists() is False
    # Other user's access is untouched
    assert models.ItemAccess.objects.filter(pk=other_access.pk).exists()
    # grandchild is still readable (it had no direct access record for user)
    assert models.Item.objects.filter(pk=grandchild.pk).exists()


def test_api_items_leave_removes_link_traces_on_subtree():
    """Leaving a parent item also removes the user's link traces on descendant items."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        link_reach="authenticated",
        link_traces=[user],
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        parent=parent,
        link_reach="authenticated",
        link_traces=[user],
    )

    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{parent.id!s}/leave/")

    assert response.status_code == 204
    assert models.LinkTrace.objects.filter(user=user).exists() is False


def test_api_items_leave_other_users_unaffected():
    """Leaving an item only removes the requesting user's access, not others'."""
    user = factories.UserFactory()
    other_user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "editor"), (other_user, "editor")])
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 204
    assert models.ItemAccess.objects.filter(item=item, user=user).exists() is False
    assert models.ItemAccess.objects.filter(item=item, user=other_user).exists()


def test_api_items_leave_with_access_and_link_trace():
    """Leaving removes both the explicit access and the link trace if both exist."""
    user = factories.UserFactory()
    item = factories.ItemFactory(
        link_reach="authenticated",
        users=[(user, "editor")],
        link_traces=[user],
    )
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id!s}/leave/")

    assert response.status_code == 204
    assert models.ItemAccess.objects.filter(item=item, user=user).exists() is False
    assert models.LinkTrace.objects.filter(item=item, user=user).exists() is False


def test_api_items_leave_does_not_affect_other_items():
    """Leaving one item does not remove the user's access on other items."""
    user = factories.UserFactory()
    item_to_leave = factories.ItemFactory(users=[(user, "editor")])
    other_item = factories.ItemFactory(users=[(user, "editor")])
    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item_to_leave.id!s}/leave/")

    assert response.status_code == 204
    assert models.ItemAccess.objects.filter(item=item_to_leave, user=user).exists() is False
    assert models.ItemAccess.objects.filter(item=other_item, user=user).exists()
