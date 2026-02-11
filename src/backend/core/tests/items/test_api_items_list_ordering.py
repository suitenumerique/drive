"""Test the ordering of items."""

import operator
from uuid import UUID

from django.utils import timezone

import pytest
from freezegun import freeze_time
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


def test_api_items_list_ordering_deterministic_tie_breaker_id():
    """
    Ordering must be deterministic for stable pagination boundaries.

    When the requested ordering fields are tied, the API must apply a stable
    tie-breaker (id) so paging does not skip/duplicate items.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    now = timezone.now()
    with freeze_time(now):
        item1 = factories.ItemFactory(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            users=[user],
            type=models.ItemTypeChoices.FOLDER,
            title="Same",
        )
        item2 = factories.ItemFactory(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            users=[user],
            type=models.ItemTypeChoices.FOLDER,
            title="Same",
        )

    response = client.get("/api/v1.0/items/?ordering=title&page_size=1&page=1")
    assert response.status_code == 200
    assert [r["id"] for r in response.json()["results"]] == [str(item1.id)]

    response = client.get("/api/v1.0/items/?ordering=title&page_size=1&page=2")
    assert response.status_code == 200
    assert [r["id"] for r in response.json()["results"]] == [str(item2.id)]
