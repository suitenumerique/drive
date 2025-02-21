"""
Tests for items API endpoint in drive's core app: list
"""

import random
from datetime import timedelta
from unittest import mock

from django.utils import timezone

import pytest
from faker import Faker
from rest_framework.pagination import PageNumberPagination
from rest_framework.test import APIClient

from core import factories, models

fake = Faker()
pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", models.LinkRoleChoices.values)
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_list_anonymous(reach, role):
    """
    Anonymous users should not be allowed to list items whatever the
    link reach and link role
    """
    factories.ItemFactory(link_reach=reach, link_role=role)

    response = APIClient().get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 0


def test_api_items_list_format():
    """Validate the format of items as returned by the list view."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    other_users = factories.UserFactory.create_batch(3)
    item = factories.ItemFactory(
        users=factories.UserFactory.create_batch(2),
        favorited_by=[user, *other_users],
        link_traces=other_users,
        type=models.ItemTypeChoices.FOLDER,
    )
    item2 = factories.ItemFactory(
        users=factories.UserFactory.create_batch(2),
        favorited_by=[user, *other_users],
        link_traces=other_users,
        type=models.ItemTypeChoices.FILE,
    )
    access = factories.UserItemAccessFactory(item=item, user=user)
    access2 = factories.UserItemAccessFactory(item=item2, user=user)

    item2.upload_state = models.ItemUploadStateChoices.UPLOADED
    item2.filename = "logo.png"
    item2.save()

    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 2,
        "next": None,
        "previous": None,
    }
    assert len(results) == 2
    assert results == [
        {
            "id": str(item2.id),
            "abilities": item2.get_abilities(user),
            "created_at": item2.created_at.isoformat().replace("+00:00", "Z"),
            "creator": str(item2.creator.id),
            "depth": 1,
            "is_favorite": True,
            "link_reach": item2.link_reach,
            "link_role": item2.link_role,
            "nb_accesses": 3,
            "numchild": 0,
            "path": str(item2.path),
            "title": item2.title,
            "updated_at": item2.updated_at.isoformat().replace("+00:00", "Z"),
            "user_roles": [access2.role],
            "type": models.ItemTypeChoices.FILE,
            "upload_state": models.ItemUploadStateChoices.UPLOADED,
            "url": f"http://localhost:8083/media/item/{item2.id!s}/logo.png",
        },
        {
            "id": str(item.id),
            "abilities": item.get_abilities(user),
            "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
            "creator": str(item.creator.id),
            "depth": 1,
            "is_favorite": True,
            "link_reach": item.link_reach,
            "link_role": item.link_role,
            "nb_accesses": 3,
            "numchild": 0,
            "path": str(item.path),
            "title": item.title,
            "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
            "user_roles": [access.role],
            "type": models.ItemTypeChoices.FOLDER,
            "upload_state": None,
            "url": None,
        },
    ]


# pylint: disable=too-many-locals
def test_api_items_list_authenticated_direct(django_assert_num_queries):
    """
    Authenticated users should be able to list items they are a direct
    owner/administrator/member of or items that have a link reach other
    than restricted.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item1, item2 = [
        access.item
        for access in factories.UserItemAccessFactory.create_batch(
            2, user=user, item__type=models.ItemTypeChoices.FOLDER
        )
    ]

    # Unrelated and untraced items
    for reach in models.LinkReachChoices:
        for role in models.LinkRoleChoices:
            factories.ItemFactory(link_reach=reach, link_role=role)

    # Children of visible items should not get listed even with a specific access
    factories.ItemFactory(parent=item1)

    child1_with_access = factories.ItemFactory(parent=item1)
    factories.UserItemAccessFactory(user=user, item=child1_with_access)

    middle_item = factories.ItemFactory(
        parent=item2, type=models.ItemTypeChoices.FOLDER
    )
    child2_with_access = factories.ItemFactory(parent=middle_item)
    factories.UserItemAccessFactory(user=user, item=child2_with_access)

    # Children of hidden items should get listed when visible by the logged-in user
    hidden_root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    child3_with_access = factories.ItemFactory(
        parent=hidden_root, type=models.ItemTypeChoices.FILE
    )
    factories.UserItemAccessFactory(user=user, item=child3_with_access)
    child4_with_access = factories.ItemFactory(
        parent=hidden_root, type=models.ItemTypeChoices.FILE
    )
    factories.UserItemAccessFactory(user=user, item=child4_with_access)

    # items that are soft deleted and children of a soft deleted item should not be listed
    soft_deleted_item = factories.ItemFactory(
        users=[user], type=models.ItemTypeChoices.FOLDER
    )
    child_of_soft_deleted_item = factories.ItemFactory(
        users=[user],
        parent=soft_deleted_item,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(users=[user], parent=child_of_soft_deleted_item)
    soft_deleted_item.soft_delete()

    # items that are permanently deleted and children of a permanently deleted
    # item should not be listed
    permanently_deleted_item = factories.ItemFactory(
        users=[user], type=models.ItemTypeChoices.FOLDER
    )
    child_of_permanently_deleted_item = factories.ItemFactory(
        users=[user],
        parent=permanently_deleted_item,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(users=[user], parent=child_of_permanently_deleted_item)

    fourty_days_ago = timezone.now() - timedelta(days=40)
    with mock.patch("django.utils.timezone.now", return_value=fourty_days_ago):
        permanently_deleted_item.soft_delete()

    expected_ids = {
        str(item1.id),
        str(item2.id),
        str(child3_with_access.id),
        str(child4_with_access.id),
    }

    with django_assert_num_queries(10):
        response = client.get("/api/v1.0/items/")

    # nb_accesses should now be cached
    with django_assert_num_queries(6):
        response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    results_ids = {result["id"] for result in results}
    assert expected_ids == results_ids


def test_api_items_list_authenticated_via_team(
    django_assert_num_queries, mock_user_teams
):
    """
    Authenticated users should be able to list items they are a
    owner/administrator/member of via a team.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    mock_user_teams.return_value = ["team1", "team2", "unknown"]

    items_team1 = [
        access.item
        for access in factories.TeamItemAccessFactory.create_batch(
            2, team="team1", item__type=models.ItemTypeChoices.FILE
        )
    ]
    items_team2 = [
        access.item
        for access in factories.TeamItemAccessFactory.create_batch(
            3, team="team2", item__type=models.ItemTypeChoices.FILE
        )
    ]

    expected_ids = {str(item.id) for item in items_team1 + items_team2}

    with django_assert_num_queries(9):
        response = client.get("/api/v1.0/items/")

    # nb_accesses should now be cached
    with django_assert_num_queries(4):
        response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5
    results_id = {result["id"] for result in results}
    assert expected_ids == results_id


def test_api_items_list_authenticated_link_reach_restricted(
    django_assert_num_queries,
):
    """
    An authenticated user who has link traces to a item that is restricted should not
    see it on the list view
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_traces=[user], link_reach="restricted", type=models.ItemTypeChoices.FILE
    )

    # Link traces for other items or other users should not interfere
    models.LinkTrace.objects.create(item=item, user=factories.UserFactory())
    other_item = factories.ItemFactory(
        link_reach="public", type=models.ItemTypeChoices.FILE
    )
    models.LinkTrace.objects.create(item=other_item, user=user)

    with django_assert_num_queries(5):
        response = client.get("/api/v1.0/items/")

    # nb_accesses should now be cached
    with django_assert_num_queries(4):
        response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    # Only the other item is returned but not the restricted item even though the user
    # visited it earlier (probably b/c it previously had public or authenticated reach...)
    assert len(results) == 1
    assert results[0]["id"] == str(other_item.id)


def test_api_items_list_authenticated_link_reach_public_or_authenticated(
    django_assert_num_queries,
):
    """
    An authenticated user who has link traces to a item with public or authenticated
    link reach should see it on the list view.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item1, item2 = [
        factories.ItemFactory(
            link_traces=[user], link_reach=reach, type=models.ItemTypeChoices.FOLDER
        )
        for reach in models.LinkReachChoices
        if reach != "restricted"
    ]
    factories.ItemFactory(
        link_reach=random.choice(["public", "authenticated"]),
        link_traces=[user],
        parent=item1,
    )

    hidden_item = factories.ItemFactory(
        link_reach=random.choice(["public", "authenticated"]),
        type=models.ItemTypeChoices.FOLDER,
    )
    visible_child = factories.ItemFactory(
        link_traces=[user],
        link_reach=random.choice(["public", "authenticated"]),
        parent=hidden_item,
        type=models.ItemTypeChoices.FILE,
    )

    expected_ids = {str(item1.id), str(item2.id), str(visible_child.id)}

    with django_assert_num_queries(9):
        response = client.get("/api/v1.0/items/")

    # nb_accesses should now be cached
    with django_assert_num_queries(6):
        response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    results_id = {result["id"] for result in results}
    assert expected_ids == results_id


@mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
def test_api_items_list_pagination(
    _mock_page_size,
):
    """Pagination should work as expected."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item_ids = [
        str(access.item_id)
        for access in factories.UserItemAccessFactory.create_batch(3, user=user)
    ]

    # Get page 1
    response = client.get(
        "/api/v1.0/items/",
    )

    assert response.status_code == 200
    content = response.json()

    assert content["count"] == 3
    assert content["next"] == "http://testserver/api/v1.0/items/?page=2"
    assert content["previous"] is None

    assert len(content["results"]) == 2
    for item in content["results"]:
        item_ids.remove(item["id"])

    # Get page 2
    response = client.get(
        "/api/v1.0/items/?page=2",
    )

    assert response.status_code == 200
    content = response.json()

    assert content["count"] == 3
    assert content["next"] is None
    assert content["previous"] == "http://testserver/api/v1.0/items/"

    assert len(content["results"]) == 1
    item_ids.remove(content["results"][0]["id"])
    assert item_ids == []


def test_api_items_list_authenticated_distinct():
    """A item with several related users should only be listed once."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    other_user = factories.UserFactory()

    item = factories.ItemFactory(users=[user, other_user])

    response = client.get(
        "/api/v1.0/items/",
    )

    assert response.status_code == 200
    content = response.json()
    assert len(content["results"]) == 1
    assert content["results"][0]["id"] == str(item.id)


def test_api_items_list_favorites_no_extra_queries(django_assert_num_queries):
    """
    Ensure that marking items as favorite does not generate additional queries
    when fetching the item list.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    special_items = factories.ItemFactory.create_batch(
        3, users=[user], type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory.create_batch(
        2, users=[user], type=models.ItemTypeChoices.FILE
    )

    url = "/api/v1.0/items/"
    with django_assert_num_queries(9):
        response = client.get(url)

    # nb_accesses should now be cached
    with django_assert_num_queries(4):
        response = client.get(url)

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5

    assert all(result["is_favorite"] is False for result in results)

    # Mark items as favorite and check results again
    for item in special_items:
        models.ItemFavorite.objects.create(item=item, user=user)

    with django_assert_num_queries(4):
        response = client.get(url)

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5

    # Check if the "is_favorite" annotation is correctly set for the favorited items
    favorited_ids = {str(doc.id) for doc in special_items}
    for result in results:
        if result["id"] in favorited_ids:
            assert result["is_favorite"] is True
        else:
            assert result["is_favorite"] is False
