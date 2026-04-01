"""Test the ordering of items."""

import operator

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_list_ordering_title():
    """Validate the ordering of items by title."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        users=[user],
        title="Abcd",
        type=models.ItemTypeChoices.FOLDER,
    )
    item2 = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER, title="Zyxc")

    # ordering by title ascendant (item1 and then item2)
    response = client.get("/api/v1.0/items/?ordering=title")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 2,
        "next": None,
        "previous": None,
    }
    assert len(results) == 2
    assert results[0]["id"] == str(item.id)
    assert results[1]["id"] == str(item2.id)

    # ordering by title descendant (item2 and then item1)
    response = client.get("/api/v1.0/items/?ordering=-title")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 2,
        "next": None,
        "previous": None,
    }
    assert len(results) == 2
    assert results[0]["id"] == str(item2.id)
    assert results[1]["id"] == str(item.id)


def test_api_items_list_ordering_default():
    """items should be ordered by descending "updated_at" by default"""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(4, users=[user], type=models.ItemTypeChoices.FOLDER)

    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 4

    # Check that results are sorted by descending "updated_at" as expected
    for i in range(3):
        assert operator.ge(results[i]["updated_at"], results[i + 1]["updated_at"])


def test_api_items_list_ordering_by_fields(django_assert_num_queries):
    """It should be possible to order by several fields"""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(4, users=[user], type=models.ItemTypeChoices.FOLDER)

    # make a first fetch to put in cache some sql queries and have a constant number
    # of queries later
    with django_assert_num_queries(9):
        client.get("/api/v1.0/items/")

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

        with django_assert_num_queries(5):
            response = client.get(f"/api/v1.0/items/{querystring:s}")
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 4

        # Check that results are sorted by the field in querystring as expected
        compare = operator.ge if is_descending else operator.le
        for i in range(3):
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


def test_api_items_list_ordering_by_size():
    """Test ordering files by size"""

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, creator=user, users=[(user, "owner")]
    )

    file1 = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        size=100,
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, "owner")],
    )

    file2 = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        size=200,
        update_upload_state=models.ItemUploadStateChoices.READY,
        creator=user,
        users=[(user, "owner")],
    )

    response = client.get("/api/v1.0/items/?ordering=size")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3

    assert results[0]["id"] == str(file1.id)
    assert results[1]["id"] == str(file2.id)
    assert results[2]["id"] == str(folder.id)

    response = client.get("/api/v1.0/items/?ordering=-size")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3

    assert results[0]["id"] == str(folder.id)
    assert results[1]["id"] == str(file2.id)
    assert results[2]["id"] == str(file1.id)


def test_api_items_list_ordering_by_creator_fullname(django_assert_num_queries):
    """Test ordering items by creator full_name"""

    user1 = factories.UserFactory(full_name="Camille Clement", short_name="camille")
    user2 = factories.UserFactory(full_name="Eva Roussel", short_name="Eva")
    user3 = factories.UserFactory(full_name="Olivia Pierre", short_name="Olivia")

    item1 = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor"), (user3, "editor")],
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    item2 = factories.ItemFactory(
        creator=user2,
        users=[(user2, "owner"), (user1, "editor"), (user3, "editor")],
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    item3 = factories.ItemFactory(
        creator=user3,
        users=[(user3, "owner"), (user1, "editor"), (user2, "editor")],
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    client = APIClient()
    client.force_login(user1)

    with django_assert_num_queries(8):
        response = client.get("/api/v1.0/items/?ordering=creator__full_name")

    assert response.status_code == 200

    results = response.json()["results"]
    assert len(results) == 3

    assert results[0]["id"] == str(item1.id)
    assert results[1]["id"] == str(item2.id)
    assert results[2]["id"] == str(item3.id)

    with django_assert_num_queries(5):
        response = client.get("/api/v1.0/items/?ordering=-creator__full_name")

    assert response.status_code == 200

    results = response.json()["results"]
    assert len(results) == 3

    assert results[0]["id"] == str(item3.id)
    assert results[1]["id"] == str(item2.id)
    assert results[2]["id"] == str(item1.id)
