"""Test for the document recents endpoint."""

import pytest
from rest_framework.test import APIClient

from datetime import datetime
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
    child_item_child.updated_at = datetime.now()
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

