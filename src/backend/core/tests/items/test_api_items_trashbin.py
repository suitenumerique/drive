"""
Tests for items API endpoint in drive's core app: list
"""

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
def test_api_items_trashbin_anonymous(reach, role):
    """
    Anonymous users should not be allowed to list items from the trashbin
    whatever the link reach and link role
    """
    factories.ItemFactory(link_reach=reach, link_role=role, deleted_at=timezone.now())

    response = APIClient().get("/api/v1.0/items/trashbin/")

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_api_items_trashbin_format():
    """Validate the format of items as returned by the trashbin view."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    other_users = factories.UserFactory.create_batch(3)
    item = factories.ItemFactory(
        deleted_at=timezone.now(),
        users=factories.UserFactory.create_batch(2),
        favorited_by=[user, *other_users],
        link_traces=other_users,
    )
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    response = client.get("/api/v1.0/items/trashbin/")

    assert response.status_code == 200

    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 1,
        "next": None,
        "previous": None,
    }
    assert len(results) == 1
    assert results[0] == {
        "id": str(item.id),
        "abilities": {
            "accesses_manage": True,
            "accesses_view": True,
            "children_create": True,
            "children_list": True,
            "destroy": True,
            "favorite": True,
            "invite_owner": True,
            "link_configuration": True,
            "media_auth": True,
            "move": False,  # Can't move a deleted item
            "partial_update": True,
            "restore": True,
            "retrieve": True,
            "tree": True,
            "update": True,
            "upload_ended": True,
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": str(item.creator.id),
        "depth": 1,
        "link_reach": item.link_reach,
        "link_role": item.link_role,
        "nb_accesses": 3,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": ["owner"],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
    }


def test_api_items_trashbin_authenticated_direct(django_assert_num_queries):
    """
    The trashbin should only list deleted items for which the current user is owner.
    """
    now = timezone.now()
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item1, item2 = factories.ItemFactory.create_batch(
        2, deleted_at=now, type=models.ItemTypeChoices.FOLDER
    )
    models.ItemAccess.objects.create(item=item1, user=user, role="owner")
    models.ItemAccess.objects.create(item=item2, user=user, role="owner")

    # Unrelated items
    for reach in models.LinkReachChoices:
        for role in models.LinkRoleChoices:
            factories.ItemFactory(link_reach=reach, link_role=role, deleted_at=now)

    # Role other than "owner"
    for role in models.RoleChoices.values:
        if role == "owner":
            continue
        item_not_owner = factories.ItemFactory(deleted_at=now)
        models.ItemAccess.objects.create(item=item_not_owner, user=user, role=role)

    # Nested items should also get listed
    parent = factories.ItemFactory(parent=item1, type=models.ItemTypeChoices.FOLDER)
    item3 = factories.ItemFactory(
        parent=parent, deleted_at=now, type=models.ItemTypeChoices.FILE
    )
    models.ItemAccess.objects.create(item=parent, user=user, role="owner")

    # Permanently deleted items should not be listed
    fourty_days_ago = timezone.now() - timedelta(days=40)
    permanently_deleted_item = factories.ItemFactory(users=[(user, "owner")])
    with mock.patch("django.utils.timezone.now", return_value=fourty_days_ago):
        permanently_deleted_item.soft_delete()

    expected_ids = {str(item1.id), str(item2.id), str(item3.id)}

    with django_assert_num_queries(7):
        response = client.get("/api/v1.0/items/trashbin/")

    with django_assert_num_queries(4):
        response = client.get("/api/v1.0/items/trashbin/")

    assert response.status_code == 200
    results = response.json()["results"]
    results_ids = {result["id"] for result in results}
    assert len(results) == 3
    assert expected_ids == results_ids


def test_api_items_trashbin_authenticated_via_team(
    django_assert_num_queries, mock_user_teams
):
    """
    Authenticated users should be able to list trashbin items they own via a team.
    """
    now = timezone.now()
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    mock_user_teams.return_value = ["team1", "team2", "unknown"]

    deleted_item_team1 = factories.ItemFactory(
        teams=[("team1", "owner")], deleted_at=now, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory(teams=[("team1", "owner")])
    factories.ItemFactory(teams=[("team1", "administrator")], deleted_at=now)
    factories.ItemFactory(teams=[("team1", "administrator")])
    deleted_item_team2 = factories.ItemFactory(
        teams=[("team2", "owner")], deleted_at=now, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory(teams=[("team2", "owner")])
    factories.ItemFactory(teams=[("team2", "administrator")], deleted_at=now)
    factories.ItemFactory(teams=[("team2", "administrator")])

    expected_ids = {str(deleted_item_team1.id), str(deleted_item_team2.id)}

    with django_assert_num_queries(5):
        response = client.get("/api/v1.0/items/trashbin/")

    with django_assert_num_queries(3):
        response = client.get("/api/v1.0/items/trashbin/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    results_id = {result["id"] for result in results}
    assert expected_ids == results_id


@mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
def test_api_items_trashbin_pagination(
    _mock_page_size,
):
    """Pagination should work as expected."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item_ids = [
        str(item.id)
        for item in factories.ItemFactory.create_batch(3, deleted_at=timezone.now())
    ]
    for item_id in item_ids:
        models.ItemAccess.objects.create(item_id=item_id, user=user, role="owner")

    # Get page 1
    response = client.get("/api/v1.0/items/trashbin/")

    assert response.status_code == 200
    content = response.json()

    assert content["count"] == 3
    assert content["next"] == "http://testserver/api/v1.0/items/trashbin/?page=2"
    assert content["previous"] is None

    assert len(content["results"]) == 2
    for item in content["results"]:
        item_ids.remove(item["id"])

    # Get page 2
    response = client.get(
        "/api/v1.0/items/trashbin/?page=2",
    )

    assert response.status_code == 200
    content = response.json()

    assert content["count"] == 3
    assert content["next"] is None
    assert content["previous"] == "http://testserver/api/v1.0/items/trashbin/"

    assert len(content["results"]) == 1
    item_ids.remove(content["results"][0]["id"])
    assert item_ids == []


def test_api_items_trashbin_distinct():
    """A item with several related users should only be listed once."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    other_user = factories.UserFactory()
    item = factories.ItemFactory(
        users=[(user, "owner"), other_user], deleted_at=timezone.now()
    )

    response = client.get(
        "/api/v1.0/items/trashbin/",
    )

    assert response.status_code == 200
    content = response.json()
    assert len(content["results"]) == 1
    assert content["results"][0]["id"] == str(item.id)
