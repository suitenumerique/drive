"""
Tests for items API endpoint in drive's core app: list
"""

import datetime
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


# Filters: unknown field


def test_api_items_list_filter_unknown_field():
    """
    Trying to filter by an unknown field should raise a 400 error.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    expected_ids = {
        str(item.id)
        for item in factories.ItemFactory.create_batch(
            2, users=[user], type=models.ItemTypeChoices.FOLDER
        )
    }

    response = client.get("/api/v1.0/items/?unknown=true")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert {result["id"] for result in results} == expected_ids


# Filters: is_creator_me


def test_api_items_list_filter_is_creator_me_true():
    """
    Authenticated users should be able to filter items they created.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(
        2, users=[user], creator=user, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get("/api/v1.0/items/?is_creator_me=true")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2

    # Ensure all results are created by the current user
    for result in results:
        assert result["creator"] == {
            "id": str(user.id),
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

    factories.ItemFactory.create_batch(
        3, users=[user], creator=user, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get("/api/v1.0/items/?is_creator_me=false")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2

    # Ensure all results are created by other users
    for result in results:
        assert result["creator"] != {
            "id": str(user.id),
            "full_name": user.full_name,
            "short_name": user.short_name,
        }


def test_api_items_list_filter_is_creator_me_invalid():
    """Filtering with an invalid `is_creator_me` value should do nothing."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(
        3, users=[user], creator=user, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get("/api/v1.0/items/?is_creator_me=invalid")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5


# Filters: is_favorite


def test_api_items_list_filter_is_favorite_true():
    """
    Authenticated users should be able to filter items they marked as favorite.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(
        3, users=[user], favorited_by=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, users=[user], type=models.ItemTypeChoices.FOLDER)

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

    factories.ItemFactory.create_batch(
        3, users=[user], favorited_by=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get("/api/v1.0/items/?is_favorite=false")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2

    # Ensure all results are not marked as favorite by the current user
    for result in results:
        assert result["is_favorite"] is False


def test_api_items_list_filter_is_favorite_invalid():
    """Filtering with an invalid `is_favorite` value should do nothing."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(
        3, users=[user], favorited_by=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get("/api/v1.0/items/?is_favorite=invalid")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5


# Filters: title


@pytest.mark.parametrize(
    "query,nb_results",
    [
        ("Project Alpha", 1),  # Exact match
        ("project", 2),  # Partial match (case-insensitive)
        ("Guide", 1),  # Word match within a title
        ("Special", 0),  # No match (nonexistent keyword)
        ("2024", 2),  # Match by numeric keyword
        ("", 5),  # Empty string
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
        factories.ItemFactory(
            title=title,
            users=[user],
            parent=parent,
            update_upload_state=models.ItemUploadStateChoices.READY,
        )

    # Perform the search query
    response = client.get(f"/api/v1.0/items/?title={query:s}")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == nb_results

    # Ensure all results contain the query in their title
    for result in results:
        assert query.lower().strip() in result["title"].lower()


# Filters: type


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
    folders_ids = {str(folder.item.id) for folder in folders}

    # create 2 files
    files = factories.UserItemAccessFactory.create_batch(
        2,
        user=user,
        item__type=models.ItemTypeChoices.FILE,
        item__update_upload_state=models.ItemUploadStateChoices.READY,
    )
    files_ids = {str(file.item.id) for file in files}

    # Filter by type: folder
    response = client.get("/api/v1.0/items/?type=folder")

    assert response.status_code == 200
    assert response.json()["count"] == 2

    results = response.json()["results"]

    # Ensure all results are folders
    results_ids = {result["id"] for result in results}
    assert results_ids == folders_ids
    for result in results:
        assert result["type"] == models.ItemTypeChoices.FOLDER

    # Filter by type: file
    response = client.get("/api/v1.0/items/?type=file")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    results = response.json()["results"]

    # Ensure all results are files
    results_ids = {result["id"] for result in results}
    assert results_ids == files_ids
    for result in results:
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


# Filters: category


def _login():
    """Create a user and return it with an authenticated API client."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    return user, client


def _create_item(user, item_type=models.ItemTypeChoices.FOLDER, updated_at=None, **kwargs):
    """Create an item owned by the user, ready when a file, with an optional date."""
    if item_type == models.ItemTypeChoices.FILE:
        kwargs["update_upload_state"] = models.ItemUploadStateChoices.READY
    item = factories.ItemFactory(users=[user], type=item_type, **kwargs)
    if updated_at is not None:
        # `auto_now` overrides the value on save, so set it through an update query.
        models.Item.objects.filter(pk=item.pk).update(updated_at=updated_at)
    return item


def _create_files(user, *filenames):
    """Create ready files owned by the given user with the given filenames."""
    for filename in filenames:
        _create_item(user, models.ItemTypeChoices.FILE, filename=filename)


def assert_results(response, *filenames):
    """Assert the response lists exactly the files with the given filenames."""
    assert response.status_code == 200
    results = response.json()["results"]
    assert {result["filename"] for result in results} == set(filenames)


@pytest.mark.parametrize(
    "category,expected",
    [
        ("doc", {"notes.txt", "memo.docx"}),
        ("powerpoint", {"deck.pptx"}),
        ("calc", {"data.xlsx"}),
        ("pdf", {"report.pdf"}),
        ("image", {"photo.png", "scan.JPEG"}),
        ("video", {"clip.mp4"}),
        ("audio", {"song.mp3"}),
        ("archive", {"backup.zip"}),
        ("other", {"weird.xyz"}),
    ],
)
def test_api_items_list_filter_category(category, expected):
    """Filtering by a file type category returns only the files of that category."""
    user, client = _login()

    _create_files(
        user,
        "notes.txt",
        "memo.docx",
        "deck.pptx",
        "data.xlsx",
        "report.pdf",
        "photo.png",
        "scan.JPEG",
        "clip.mp4",
        "song.mp3",
        "backup.zip",
        "weird.xyz",
    )

    response = client.get(f"/api/v1.0/items/?category={category}")

    assert_results(response, *expected)


def test_api_items_list_filter_category_keeps_folders():
    """Filtering by a file type category keeps folders visible for navigation."""
    user, client = _login()

    folder = _create_item(user, models.ItemTypeChoices.FOLDER)
    pdf = _create_item(user, models.ItemTypeChoices.FILE, filename="report.pdf")
    _create_item(user, models.ItemTypeChoices.FILE, filename="photo.png")

    response = client.get("/api/v1.0/items/?category=pdf")

    assert response.status_code == 200
    results = response.json()["results"]
    assert {result["id"] for result in results} == {str(folder.id), str(pdf.id)}


def test_api_items_list_filter_category_excludes_extensionless_files():
    """A file whose name ends with a category keyword but has no dot should not match."""
    user, client = _login()

    _create_files(user, "report.pdf", "mydoc")

    response = client.get("/api/v1.0/items/?category=doc")

    assert_results(response)


def test_api_items_list_filter_category_invalid():
    """Filtering by an invalid category should raise a 400 error."""
    _, client = _login()

    response = client.get("/api/v1.0/items/?category=unknown")

    assert response.status_code == 400


# Filters: contact


def test_api_items_list_filter_contact():
    """Filtering by contact should return items shared with that contact."""
    user, client = _login()
    contact = factories.UserFactory()

    shared = factories.ItemFactory(users=[user, contact], type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get(f"/api/v1.0/items/?contact={contact.id!s}")

    assert response.status_code == 200
    results = response.json()["results"]
    assert {result["id"] for result in results} == {str(shared.id)}


def test_api_items_list_filter_contact_no_duplicates():
    """An item shared with several users should not be duplicated in the results."""
    user, client = _login()
    contact = factories.UserFactory()
    other = factories.UserFactory()

    factories.ItemFactory(users=[user, contact, other], type=models.ItemTypeChoices.FOLDER)

    response = client.get(f"/api/v1.0/items/?contact={contact.id!s}")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def test_api_items_list_filter_contact_respects_access_rights():
    """Filtering by contact must not leak items the current user cannot access."""
    _user, client = _login()
    contact = factories.UserFactory()

    # Item shared with the contact but not with the current user.
    factories.ItemFactory(
        users=[contact], link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )

    response = client.get(f"/api/v1.0/items/?contact={contact.id!s}")

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_api_items_list_filter_contact_as_creator():
    """Filtering by contact includes items the contact created and shared (shared by)."""
    user, client = _login()
    contact = factories.UserFactory()

    created_by_contact = factories.ItemFactory(
        users=[user], creator=contact, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get(f"/api/v1.0/items/?contact={contact.id!s}")

    assert response.status_code == 200
    results = response.json()["results"]
    assert {result["id"] for result in results} == {str(created_by_contact.id)}


# Filters: updated_at


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"updated_at_after": "2023-01-01", "updated_at_before": "2024-01-01"}, {"mid"}),
        ({"updated_at_after": "2024-01-01"}, {"new"}),
        ({"updated_at_before": "2021-01-01"}, {"old"}),
        (
            {"updated_at_after": "2019-01-01", "updated_at_before": "2027-01-01"},
            {"old", "mid", "new"},
        ),
        # A date-only upper bound covers the whole day: "mid" is modified at 12:30
        # on the bound day and must still be included.
        ({"updated_at_before": "2023-06-15"}, {"old", "mid"}),
    ],
)
def test_api_items_list_filter_updated_at(params, expected):
    """Filtering by a modification date range returns only items within the range."""
    user, client = _login()

    # Mix files and folders to confirm the date filter is type-agnostic.
    _create_item(
        user,
        models.ItemTypeChoices.FILE,
        updated_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
        title="old",
    )
    _create_item(
        user,
        updated_at=datetime.datetime(2023, 6, 15, 12, 30, tzinfo=datetime.UTC),
        title="mid",
    )
    _create_item(
        user,
        models.ItemTypeChoices.FILE,
        updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        title="new",
    )

    response = client.get(f"/api/v1.0/items/?{urlencode(params):s}")

    assert response.status_code == 200
    results = response.json()["results"]
    assert {result["title"] for result in results} == expected


def test_api_items_list_filter_updated_at_invalid():
    """The modification date filter only accepts dates, other values raise a 400 error."""
    _, client = _login()

    response = client.get("/api/v1.0/items/?updated_at_before=not-a-date")

    assert response.status_code == 400
