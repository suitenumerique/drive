"""
Tests for items API endpoint in drive's core app: list
"""

import operator
import random
from urllib.parse import urlencode

import pytest
from faker import Faker
from rest_framework.test import APIClient

from core import factories, models

fake = Faker()
pytestmark = pytest.mark.django_db


def test_api_items_list_filter_and_access_rights():
    """Filtering on querystring parameters should respect access rights."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    other_user = factories.UserFactory()

    def random_favorited_by():
        return random.choice([[], [user], [other_user]])

    # items that should be listed to this user
    listed_items = [
        factories.ItemFactory(
            link_reach="public",
            link_traces=[user],
            favorited_by=random_favorited_by(),
            creator=random.choice([user, other_user]),
        ),
        factories.ItemFactory(
            link_reach="authenticated",
            link_traces=[user],
            favorited_by=random_favorited_by(),
            creator=random.choice([user, other_user]),
        ),
        factories.ItemFactory(
            link_reach="restricted",
            users=[user],
            favorited_by=random_favorited_by(),
            creator=random.choice([user, other_user]),
        ),
        user.get_main_workspace(),
    ]
    listed_ids = [str(doc.id) for doc in listed_items]
    word_list = [word for doc in listed_items for word in doc.title.split(" ")]

    # items that should not be listed to this user
    factories.ItemFactory(
        link_reach="public",
        favorited_by=random_favorited_by(),
        creator=random.choice([user, other_user]),
    )
    factories.ItemFactory(
        link_reach="authenticated",
        favorited_by=random_favorited_by(),
        creator=random.choice([user, other_user]),
    )
    factories.ItemFactory(
        link_reach="restricted",
        favorited_by=random_favorited_by(),
        creator=random.choice([user, other_user]),
    )
    factories.ItemFactory(
        link_reach="restricted",
        link_traces=[user],
        favorited_by=random_favorited_by(),
        creator=random.choice([user, other_user]),
    )

    filters = {
        "link_reach": random.choice([None, *models.LinkReachChoices.values]),
        "title": random.choice([None, *word_list]),
        "favorite": random.choice([None, True, False]),
        "creator": random.choice([None, user, other_user]),
        "ordering": random.choice(
            [
                None,
                "created_at",
                "-created_at",
                "is_favorite",
                "-is_favorite",
                "title",
                "-title",
                "updated_at",
                "-updated_at",
            ]
        ),
    }
    query_params = {key: value for key, value in filters.items() if value is not None}
    querystring = urlencode(query_params)

    response = client.get(f"/api/v1.0/items/?{querystring:s}")

    assert response.status_code == 200
    results = response.json()["results"]

    # Ensure all items in results respect expected access rights
    for result in results:
        assert result["id"] in listed_ids


# Filters: ordering


def test_api_items_list_ordering_default():
    """items should be ordered by descending "updated_at" by default"""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(4, users=[user])

    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5

    # Check that results are sorted by descending "updated_at" as expected
    for i in range(4):
        assert operator.ge(results[i]["updated_at"], results[i + 1]["updated_at"])


def test_api_items_list_ordering_by_fields():
    """It should be possible to order by several fields"""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(4, users=[user])

    for parameter in [
        "created_at",
        "-created_at",
        "is_favorite",
        "-is_favorite",
        "title",
        "-title",
        "updated_at",
        "-updated_at",
    ]:
        is_descending = parameter.startswith("-")
        field = parameter.lstrip("-")
        querystring = f"?ordering={parameter}"

        response = client.get(f"/api/v1.0/items/{querystring:s}")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 5

        # Check that results are sorted by the field in querystring as expected
        compare = operator.ge if is_descending else operator.le
        for i in range(4):
            operator1 = (
                results[i][field].lower()
                if isinstance(results[i][field], str)
                else results[i][field]
            )
            operator2 = (
                results[i + 1][field].lower()
                if isinstance(results[i + 1][field], str)
                else results[i + 1][field]
            )
            assert compare(operator1, operator2)


# Filters: unknown field


def test_api_items_list_filter_unknown_field():
    """
    Trying to filter by an unknown field should raise a 400 error.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory()
    expected_ids = {
        str(item.id) for item in factories.ItemFactory.create_batch(2, users=[user])
    }
    expected_ids.add(str(user.get_main_workspace().id))

    response = client.get("/api/v1.0/items/?unknown=true")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert {result["id"] for result in results} == expected_ids


# Filters: is_creator_me


def test_api_items_list_filter_is_creator_me_true():
    """
    Authenticated users should be able to filter items they created.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(2, users=[user], creator=user)
    factories.ItemFactory.create_batch(2, users=[user])

    response = client.get("/api/v1.0/items/?is_creator_me=true")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3

    # Ensure all results are created by the current user
    for result in results:
        assert result["creator"] == {
            "full_name": user.full_name,
            "short_name": user.short_name,
        }


def test_api_items_list_filter_is_creator_me_false():
    """
    Authenticated users should be able to filter items created by others.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(3, users=[user], creator=user)
    factories.ItemFactory.create_batch(2, users=[user])

    response = client.get("/api/v1.0/items/?is_creator_me=false")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2

    # Ensure all results are created by other users
    for result in results:
        assert result["creator"] != {
            "full_name": user.full_name,
            "short_name": user.short_name,
        }


def test_api_items_list_filter_is_creator_me_invalid():
    """Filtering with an invalid `is_creator_me` value should do nothing."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(3, users=[user], creator=user)
    factories.ItemFactory.create_batch(2, users=[user])

    response = client.get("/api/v1.0/items/?is_creator_me=invalid")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 6


# Filters: is_favorite


def test_api_items_list_filter_is_favorite_true():
    """
    Authenticated users should be able to filter items they marked as favorite.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(3, users=[user], favorited_by=[user])
    factories.ItemFactory.create_batch(2, users=[user])

    response = client.get("/api/v1.0/items/?is_favorite=true")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3

    # Ensure all results are marked as favorite by the current user
    for result in results:
        assert result["is_favorite"] is True


def test_api_items_list_filter_is_favorite_false():
    """
    Authenticated users should be able to filter items they didn't mark as favorite.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(3, users=[user], favorited_by=[user])
    factories.ItemFactory.create_batch(2, users=[user])

    response = client.get("/api/v1.0/items/?is_favorite=false")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3

    # Ensure all results are not marked as favorite by the current user
    for result in results:
        assert result["is_favorite"] is False


def test_api_items_list_filter_is_favorite_invalid():
    """Filtering with an invalid `is_favorite` value should do nothing."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(3, users=[user], favorited_by=[user])
    factories.ItemFactory.create_batch(2, users=[user])

    response = client.get("/api/v1.0/items/?is_favorite=invalid")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 6


# Filters: title


@pytest.mark.parametrize(
    "query,nb_results",
    [
        ("Project Alpha", 1),  # Exact match
        ("project", 2),  # Partial match (case-insensitive)
        ("Guide", 1),  # Word match within a title
        ("Special", 0),  # No match (nonexistent keyword)
        ("2024", 2),  # Match by numeric keyword
        ("", 6),  # Empty string
    ],
)
def test_api_items_list_filter_title(query, nb_results):
    """Authenticated users should be able to search items by their title."""
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
    for title in titles:
        parent = (
            factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
            if random.choice([True, False])
            else None
        )
        factories.ItemFactory(title=title, users=[user], parent=parent)

    # Perform the search query
    response = client.get(f"/api/v1.0/items/?title={query:s}")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == nb_results

    # Ensure all results contain the query in their title
    for result in results:
        assert query.lower().strip() in result["title"].lower()


def test_api_items_list_filter_type():
    """
    Authenticated users should be able to filter items by their type.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # create 2 folders, main workspace is already a folder, means 3 folders in total
    folders = factories.UserItemAccessFactory.create_batch(
        2, user=user, item__type=models.ItemTypeChoices.FOLDER
    )
    folders_ids = [str(folder.item.id) for folder in folders] + [
        str(user.get_main_workspace().id)
    ]

    # create 2 files
    files = factories.UserItemAccessFactory.create_batch(
        2, user=user, item__type=models.ItemTypeChoices.FILE
    )
    files_ids = [str(file.item.id) for file in files]

    # Filter by type: folder
    response = client.get("/api/v1.0/items/?type=folder")
    assert response.status_code == 200

    assert response.json()["count"] == 3
    results = response.json()["results"]

    # Ensure all results are folders
    for result in results:
        assert result["id"] in folders_ids
        assert result["type"] == models.ItemTypeChoices.FOLDER

    # Filter by type: file
    response = client.get("/api/v1.0/items/?type=file")
    assert response.status_code == 200

    assert response.json()["count"] == 2
    results = response.json()["results"]

    # Ensure all results are files
    for result in results:
        assert result["id"] in files_ids
        assert result["type"] == models.ItemTypeChoices.FILE


def test_api_items_list_filter_unknown_type():
    """
    Filtering by an unknown type should return an empty list
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.UserItemAccessFactory.create_batch(3, user=user)

    response = client.get("/api/v1.0/items/?type=unknown")

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "type",
                "code": "invalid",
                "detail": "Select a valid choice. unknown is not one of the available choices.",
            },
        ],
        "type": "validation_error",
    }
