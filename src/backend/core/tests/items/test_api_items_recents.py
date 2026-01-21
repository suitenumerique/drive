"""Test for the document recents endpoint."""

from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_item_recents_anonymous():
    """Anonymous users should receive a 401 error."""

    client = APIClient()

    response = client.get("/api/v1.0/items/recents/")

    assert response.status_code == 401


def test_api_item_recents_authenticated_no_recent_items():
    """Authenticated users should receive an empty list."""

    user = factories.UserFactory()

    client = APIClient()

    client.force_login(user)

    response = client.get("/api/v1.0/items/recents/")

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_api_item_recents_authenticated_with_recent_items():
    """Authenticated users with recent items should get the recent items."""

    user = factories.UserFactory()

    client = APIClient()

    client.force_login(user)

    parent_item = factories.ItemFactory(
        creator=user,
        type=models.ItemTypeChoices.FOLDER,
        title="parent",
    )
    child_item = factories.ItemFactory(
        creator=user,
        parent=parent_item,
        type=models.ItemTypeChoices.FOLDER,
        title="child",
    )
    child_item_child = factories.ItemFactory(
        creator=user,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="child child file",
    )
    child_item_file = factories.ItemFactory(
        creator=user,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="child file",
    )

    parent2_item = factories.ItemFactory(
        creator=user,
        type=models.ItemTypeChoices.FOLDER,
        title="parent 2",
    )
    child2_item_file = factories.ItemFactory(
        creator=user,
        parent=parent2_item,
        type=models.ItemTypeChoices.FILE,
        title="child 2 file",
    )

    # Make this item the most recent item.
    child_item_child.updated_at = timezone.now()
    child_item_child.save()

    factories.UserItemAccessFactory(item=parent_item, user=user)
    factories.UserItemAccessFactory(item=parent2_item, user=user)

    response = client.get("/api/v1.0/items/recents/")
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 6
    assert content["results"][0]["id"] == str(child_item_child.id)
    assert content["results"][1]["id"] == str(child2_item_file.id)
    assert content["results"][2]["id"] == str(parent2_item.id)
    assert content["results"][3]["id"] == str(child_item_file.id)
    assert content["results"][4]["id"] == str(child_item.id)
    assert content["results"][5]["id"] == str(parent_item.id)


def test_api_items_recents_mixing_explicit_and_inherited_accesses(
    django_assert_num_queries,
):
    """
    Test that the recents endpoint correctly handles mixing of explicit and inherited accesses.
    """
    user = factories.UserFactory()
    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    items = factories.ItemFactory.create_batch(
        3, parent=parent, type=models.ItemTypeChoices.FILE, update_upload_state="ready"
    )

    # not accessible items
    other_root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory.create_batch(
        3,
        parent=other_root,
        type=models.ItemTypeChoices.FILE,
        update_upload_state="ready",
    )

    # other accessible items in an other tree
    other_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    other_items = factories.ItemFactory.create_batch(
        3,
        parent=other_parent,
        type=models.ItemTypeChoices.FILE,
        update_upload_state="ready",
    )
    factories.UserItemAccessFactory(item=other_parent, user=user, role="editor")

    # Give access to the user to the parent item
    access = factories.UserItemAccessFactory(item=parent, user=user, role="editor")
    assert access.user == user

    # modify parent
    parent.updated_at = timezone.now()
    parent.save()

    # modify 1 item
    items[0].updated_at = timezone.now()
    items[0].save()

    # modify 1 other item
    other_items[0].updated_at = timezone.now()
    other_items[0].save()

    client = APIClient()
    client.force_login(user)

    with django_assert_num_queries(6):
        response = client.get("/api/v1.0/items/recents/")
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 8
    assert content["results"][0]["id"] == str(other_items[0].id)
    assert content["results"][1]["id"] == str(items[0].id)
    assert content["results"][2]["id"] == str(parent.id)
    assert content["results"][3]["id"] == str(other_items[2].id)
    assert content["results"][4]["id"] == str(other_items[1].id)
    assert content["results"][5]["id"] == str(other_parent.id)
    assert content["results"][6]["id"] == str(items[2].id)
    assert content["results"][7]["id"] == str(items[1].id)
