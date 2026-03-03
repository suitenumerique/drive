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
    item2 = factories.ItemFactory(
        users=[user], type=models.ItemTypeChoices.FOLDER, title="Zyxc"
    )

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

    factories.ItemFactory.create_batch(
        4, users=[user], type=models.ItemTypeChoices.FOLDER
    )

    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 4

    # Check that results are sorted by descending "updated_at" as expected
    for i in range(3):
        assert operator.ge(results[i]["updated_at"], results[i + 1]["updated_at"])


def test_api_items_list_ordering_size():
    """Validate the ordering of items by size."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item_small = factories.ItemFactory(
        users=[user],
        title="small_file",
        type=models.ItemTypeChoices.FILE,
        size=100,
    )
    item_large = factories.ItemFactory(
        users=[user],
        title="large_file",
        type=models.ItemTypeChoices.FILE,
        size=999999,
    )
    item_no_size = factories.ItemFactory(
        users=[user],
        title="folder_no_size",
        type=models.ItemTypeChoices.FOLDER,
        size=None,
    )

    # Ascending: small, large, then nulls last (PostgreSQL default)
    response = client.get("/api/v1.0/items/?ordering=size")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["id"] == str(item_small.id)
    assert results[1]["id"] == str(item_large.id)
    assert results[2]["id"] == str(item_no_size.id)

    # Descending: nulls first (PostgreSQL default), then large, then small
    response = client.get("/api/v1.0/items/?ordering=-size")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["id"] == str(item_no_size.id)
    assert results[1]["id"] == str(item_large.id)
    assert results[2]["id"] == str(item_small.id)


def test_api_items_list_ordering_creator():
    """Validate the ordering of items by creator full name."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    creator_a = factories.UserFactory(full_name="Alice")
    creator_z = factories.UserFactory(full_name="Zara")

    item_a = factories.ItemFactory(
        users=[user],
        title="item_by_alice",
        type=models.ItemTypeChoices.FOLDER,
        creator=creator_a,
    )
    item_z = factories.ItemFactory(
        users=[user],
        title="item_by_zara",
        type=models.ItemTypeChoices.FOLDER,
        creator=creator_z,
    )

    # Ascending: Alice before Zara
    response = client.get("/api/v1.0/items/?ordering=creator__full_name")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_a.id)
    assert results[1]["id"] == str(item_z.id)

    # Descending: Zara before Alice
    response = client.get("/api/v1.0/items/?ordering=-creator__full_name")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_z.id)
    assert results[1]["id"] == str(item_a.id)


def test_api_items_list_ordering_mime_category():
    """Validate that ordering by mime_category groups items by display category."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item_pdf = factories.ItemFactory(
        users=[user],
        title="doc.pdf",
        type=models.ItemTypeChoices.FILE,
        mimetype="application/pdf",
    )
    item_image = factories.ItemFactory(
        users=[user],
        title="photo.png",
        type=models.ItemTypeChoices.FILE,
        mimetype="image/png",
    )
    item_other = factories.ItemFactory(
        users=[user],
        title="notes.md",
        type=models.ItemTypeChoices.FILE,
        mimetype="text/markdown",
    )

    # Ascending: image < other < pdf (alphabetical)
    response = client.get("/api/v1.0/items/?ordering=mime_category")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3

    result_ids = [r["id"] for r in results]
    assert result_ids.index(str(item_image.id)) < result_ids.index(str(item_other.id))
    assert result_ids.index(str(item_other.id)) < result_ids.index(str(item_pdf.id))

    # Descending: pdf > other > image
    response = client.get("/api/v1.0/items/?ordering=-mime_category")
    assert response.status_code == 200
    results = response.json()["results"]
    result_ids = [r["id"] for r in results]
    assert result_ids.index(str(item_pdf.id)) < result_ids.index(str(item_other.id))
    assert result_ids.index(str(item_other.id)) < result_ids.index(str(item_image.id))


def test_api_items_list_ordering_by_fields():
    """It should be possible to order by several fields"""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    factories.ItemFactory.create_batch(
        4, users=[user], type=models.ItemTypeChoices.FOLDER
    )

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
