"""Test favorite item API endpoint for users in drive's core app."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "reach",
    [
        "restricted",
        "authenticated",
        "public",
    ],
)
@pytest.mark.parametrize("method", ["post", "delete"])
def test_api_item_favorite_anonymous_user(method, reach):
    """Anonymous users should not be able to mark/unmark items as favorites."""
    item = factories.ItemFactory(link_reach=reach)

    response = getattr(APIClient(), method)(f"/api/v1.0/items/{item.id!s}/favorite/")

    assert response.status_code == 401
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

    # Verify in database
    assert models.ItemFavorite.objects.exists() is False


@pytest.mark.parametrize(
    "reach, has_role",
    [
        ["restricted", True],
        ["authenticated", False],
        ["authenticated", True],
        ["public", False],
        ["public", True],
    ],
)
def test_api_item_favorite_authenticated_post_allowed(reach, has_role):
    """Authenticated users should be able to mark a item as favorite using POST."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=reach)
    client = APIClient()
    client.force_login(user)

    if has_role:
        models.ItemAccess.objects.create(item=item, user=user)

    # Mark as favorite
    response = client.post(f"/api/v1.0/items/{item.id!s}/favorite/")

    assert response.status_code == 201
    assert response.json() == {"detail": "item marked as favorite"}

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists()

    # Verify item format
    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.json()["is_favorite"] is True


def test_api_item_favorite_authenticated_post_forbidden():
    """Authenticated users should be able to mark a item as favorite using POST."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="restricted")
    client = APIClient()
    client.force_login(user)

    # Try marking as favorite
    response = client.post(f"/api/v1.0/items/{item.id!s}/favorite/")

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

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists() is False


@pytest.mark.parametrize(
    "reach, has_role",
    [
        ["restricted", True],
        ["authenticated", False],
        ["authenticated", True],
        ["public", False],
        ["public", True],
    ],
)
def test_api_item_favorite_authenticated_post_already_favorited_allowed(
    reach, has_role
):
    """POST should not create duplicate favorites if already marked."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=reach, favorited_by=[user])
    client = APIClient()
    client.force_login(user)

    if has_role:
        models.ItemAccess.objects.create(item=item, user=user)

    # Try to mark as favorite again
    response = client.post(f"/api/v1.0/items/{item.id!s}/favorite/")

    assert response.status_code == 200
    assert response.json() == {"detail": "item already marked as favorite"}

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists()

    # Verify item format
    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.json()["is_favorite"] is True


def test_api_item_favorite_authenticated_post_already_favorited_forbidden():
    """POST should not create duplicate favorites if already marked."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="restricted", favorited_by=[user])
    client = APIClient()
    client.force_login(user)

    # Try to mark as favorite again
    response = client.post(f"/api/v1.0/items/{item.id!s}/favorite/")

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

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists()


@pytest.mark.parametrize(
    "reach, has_role",
    [
        ["restricted", True],
        ["authenticated", False],
        ["authenticated", True],
        ["public", False],
        ["public", True],
    ],
)
def test_api_item_favorite_authenticated_delete_allowed(reach, has_role):
    """Authenticated users should be able to unmark a item as favorite using DELETE."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=reach, favorited_by=[user])
    client = APIClient()
    client.force_login(user)

    if has_role:
        models.ItemAccess.objects.create(item=item, user=user)

    # Unmark as favorite
    response = client.delete(f"/api/v1.0/items/{item.id!s}/favorite/")
    assert response.status_code == 204

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists() is False

    # Verify item format
    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.json()["is_favorite"] is False


def test_api_item_favorite_authenticated_delete_forbidden():
    """Authenticated users should be able to unmark a item as favorite using DELETE."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="restricted", favorited_by=[user])
    client = APIClient()
    client.force_login(user)

    # Unmark as favorite
    response = client.delete(f"/api/v1.0/items/{item.id!s}/favorite/")

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

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists() is True


@pytest.mark.parametrize(
    "reach, has_role",
    [
        ["restricted", True],
        ["authenticated", False],
        ["authenticated", True],
        ["public", False],
        ["public", True],
    ],
)
def test_api_item_favorite_authenticated_delete_not_favorited_allowed(reach, has_role):
    """DELETE should be idempotent if the item is not marked as favorite."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=reach)
    client = APIClient()
    client.force_login(user)

    if has_role:
        models.ItemAccess.objects.create(item=item, user=user)

    # Try to unmark as favorite when no favorite entry exists
    response = client.delete(f"/api/v1.0/items/{item.id!s}/favorite/")

    assert response.status_code == 200
    assert response.json() == {"detail": "item was already not marked as favorite"}

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists() is False

    # Verify item format
    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.json()["is_favorite"] is False


def test_api_item_favorite_authenticated_delete_not_favorited_forbidden():
    """DELETE should be idempotent if the item is not marked as favorite."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="restricted")
    client = APIClient()
    client.force_login(user)

    # Try to unmark as favorite when no favorite entry exists
    response = client.delete(f"/api/v1.0/items/{item.id!s}/favorite/")

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

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists() is False


@pytest.mark.parametrize(
    "reach, has_role",
    [
        ["restricted", True],
        ["authenticated", False],
        ["authenticated", True],
        ["public", False],
        ["public", True],
    ],
)
def test_api_item_favorite_authenticated_post_unmark_then_mark_again_allowed(
    reach, has_role
):
    """A user should be able to mark, unmark, and mark a item again as favorite."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=reach)
    client = APIClient()
    client.force_login(user)

    if has_role:
        models.ItemAccess.objects.create(item=item, user=user)

    url = f"/api/v1.0/items/{item.id!s}/favorite/"

    # Mark as favorite
    response = client.post(url)
    assert response.status_code == 201

    # Unmark as favorite
    response = client.delete(url)
    assert response.status_code == 204

    # Mark as favorite again
    response = client.post(url)
    assert response.status_code == 201
    assert response.json() == {"detail": "item marked as favorite"}

    # Verify in database
    assert models.ItemFavorite.objects.filter(item=item, user=user).exists()

    # Verify item format
    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.json()["is_favorite"] is True
