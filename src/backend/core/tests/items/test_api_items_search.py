"""Tests for the Item viewset search method."""

import random

import pytest
from faker import Faker
from rest_framework.test import APIClient

from core import factories, models

fake = Faker()
pytestmark = pytest.mark.django_db


def test_api_items_search_anonymous():
    """Anonymous users should not be able to search for items."""
    client = APIClient()
    response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 401


def test_api_items_search_authenticated_without_filters():
    """
    Authenticated users should be able to search for items.
    Without filters, all the items the user has access to should be returned.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    children = factories.ItemFactory(
        title="Item 2", parent=top_parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory(title="Item 3")

    response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 200
    assert response.data["count"] == 3

    results = response.json()["results"]
    assert results[0]["id"] == str(user.get_main_workspace().id)
    assert results[1]["id"] == str(top_parent.id)
    assert results[2]["id"] == str(children.id)


@pytest.mark.parametrize(
    "query,nb_results",
    [
        ("Project Alpha", 1),  # Exact match
        ("project", 2),  # Partial match (case-insensitive)
        ("Guide", 1),  # Word match within a title
        ("Special", 0),  # No match (nonexistent keyword)
        ("2024", 2),  # Match by numeric keyword
    ],
)
def test_api_items_search_authenticated_with_title_filter(query, nb_results):
    """
    Authenticated users should be able to search for items by title.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Create items with predefined titles
    titles = [
        "Project Alpha itemation",
        "Project Beta Overview",
        "User Guide",
        "Financial Report 2024",
        "Annual Review 2024",
    ]
    top_parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    non_accessible_top_parent = factories.ItemFactory(
        title="Item 3", type=models.ItemTypeChoices.FOLDER
    )
    for title in titles:
        parent = (
            factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, parent=top_parent)
            if random.choice([True, False])
            else top_parent
        )
        factories.ItemFactory(title=title, parent=parent)
        factories.ItemFactory(title=title, parent=non_accessible_top_parent)

    response = client.get(f"/api/v1.0/items/search/?title={query:s}")
    assert response.status_code == 200
    assert response.data["count"] == nb_results


def test_api_items_search_authenticated_by_type():
    """
    Authenticated users should be able to search for items by type.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=top_parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory.create_batch(
        3, parent=top_parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=user.get_main_workspace(), type=models.ItemTypeChoices.FILE
    )

    response = client.get("/api/v1.0/items/search/?type=file")
    assert response.status_code == 200
    assert response.data["count"] == 6

    response = client.get("/api/v1.0/items/search/?type=folder")
    assert response.status_code == 200
    assert response.data["count"] == 5


def test_api_items_search_authenticated_by_workspace():
    """
    Authenticated users should be able to search for items by workspace.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory.create_batch(
        3, parent=parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=user.get_main_workspace(), type=models.ItemTypeChoices.FILE
    )

    response = client.get(f"/api/v1.0/items/search/?workspace={parent.id}")
    assert response.status_code == 200
    assert response.data["count"] == 7  # 6 children + 1 parent

    response = client.get(
        f"/api/v1.0/items/search/?workspace={user.get_main_workspace().id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == 4  # 3 children + 1 parent


def test_api_items_search_authenticated_combined_filters():
    """
    Authenticated users should be able to search for items by combining multiple filters.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parents = factories.ItemFactory.create_batch(
        3, users=[user], type=models.ItemTypeChoices.FOLDER
    )
    # Create items with predefined titles
    titles = [
        "Project Alpha itemation",
        "Project Beta Overview",
        "User Guide",
        "Financial Report 2024",
        "Annual Review 2024",
    ]
    parent_childrens = {parent.id: [] for parent in parents}
    for title in titles:
        parent = random.choice(parents)
        children = factories.ItemFactory(
            title=title, parent=parent, type=models.ItemTypeChoices.FILE
        )
        factories.ItemFactory(
            title=title,
            parent=user.get_main_workspace(),
            type=models.ItemTypeChoices.FILE,
        )
        parent_childrens[parent.id].append(children)

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={parents[0].id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == len(parent_childrens[parents[0].id])

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={parents[1].id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == len(parent_childrens[parents[1].id])

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={parents[2].id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == len(parent_childrens[parents[2].id])

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={user.get_main_workspace().id}&title=Project"
    )
    assert response.status_code == 200
    assert response.data["count"] == 2


def test_api_items_search_authenticated_filter_with_unaccessibile_workspace():
    """
    Authenticated users should not be able to search for items in unaccessible workspaces.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    unaccessible_workspace = factories.ItemFactory(
        title="Item 1", type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=unaccessible_workspace, type=models.ItemTypeChoices.FILE
    )

    response = client.get(
        f"/api/v1.0/items/search/?workspace={unaccessible_workspace.id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == 0


def test_api_items_search_authenticated_filter_with_workspace_children():
    """
    Authenticated users should not be able to filter using a folder with depth > 1
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    children = factories.ItemFactory(
        title="Item 2", parent=parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=children, type=models.ItemTypeChoices.FILE
    )

    response = client.get(f"/api/v1.0/items/search/?workspace={parent.id}&type=file")
    assert response.status_code == 200
    assert response.data["count"] == 3

    response = client.get(f"/api/v1.0/items/search/?workspace={children.id}")
    assert response.status_code == 200
    assert response.data["count"] == 0
