"""Test the ordering of items."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_children_ordering_type():
    """Validate the ordering of items by type."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    other_users = factories.UserFactory.create_batch(3)
    root = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=root,
        users=factories.UserFactory.create_batch(2),
        favorited_by=[user, *other_users],
        link_traces=other_users,
        type=models.ItemTypeChoices.FOLDER,
    )
    item2 = factories.ItemFactory(
        parent=root,
        users=factories.UserFactory.create_batch(2),
        favorited_by=[user, *other_users],
        link_traces=other_users,
        type=models.ItemTypeChoices.FILE,
    )
    factories.UserItemAccessFactory(item=item, user=user)
    factories.UserItemAccessFactory(item=item2, user=user)

    item2.upload_state = models.ItemUploadStateChoices.UPLOADED
    item2.filename = "logo.png"
    item2.save()

    # ordering by type ascendant (FILE first then FOLDER)
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=type")

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

    # ordering by type descendant (FOLDER first then FILE)
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=-type")

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


def test_api_items_children_ordering_title():
    """Validate the ordering of items by title."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(
        parent=root,
        users=[user],
        title="Abcd",
        type=models.ItemTypeChoices.FOLDER,
    )
    item2 = factories.ItemFactory(
        parent=root,
        users=[user],
        type=models.ItemTypeChoices.FILE,
        title="Zyxc",
    )

    item2.upload_state = models.ItemUploadStateChoices.UPLOADED
    item2.filename = "logo.png"
    item2.save()

    # ordering by title ascendant (item1 and then item2)
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=title")

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
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=-title")

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


def test_api_items_children_ordering_combining_type_and_title():
    """Validate the ordering of items by type and title."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)
    item1 = factories.ItemFactory(
        parent=root,
        users=[user],
        type=models.ItemTypeChoices.FILE,
        title="Abcd",
    )
    item2 = factories.ItemFactory(
        parent=root,
        users=[user],
        type=models.ItemTypeChoices.FILE,
        title="Zyxc",
    )
    item3 = factories.ItemFactory(
        parent=root,
        users=[user],
        type=models.ItemTypeChoices.FOLDER,
        title="Qrst",
    )
    item4 = factories.ItemFactory(
        parent=root,
        users=[user],
        type=models.ItemTypeChoices.FOLDER,
        title="Mnop",
    )

    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=type,title")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 4,
        "next": None,
        "previous": None,
    }
    assert len(results) == 4
    assert results[0]["id"] == str(item1.id)
    assert results[1]["id"] == str(item2.id)
    assert results[2]["id"] == str(item4.id)
    assert results[3]["id"] == str(item3.id)

    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=type,-title")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 4,
        "next": None,
        "previous": None,
    }
    assert len(results) == 4
    assert results[0]["id"] == str(item2.id)
    assert results[1]["id"] == str(item1.id)
    assert results[2]["id"] == str(item3.id)
    assert results[3]["id"] == str(item4.id)

    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=-type,-title")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 4,
        "next": None,
        "previous": None,
    }
    assert len(results) == 4
    assert results[0]["id"] == str(item3.id)
    assert results[1]["id"] == str(item4.id)
    assert results[2]["id"] == str(item2.id)
    assert results[3]["id"] == str(item1.id)

    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=-type,title")

    assert response.status_code == 200
    content = response.json()
    results = content.pop("results")
    assert content == {
        "count": 4,
        "next": None,
        "previous": None,
    }
    assert len(results) == 4
    assert results[0]["id"] == str(item4.id)
    assert results[1]["id"] == str(item3.id)
    assert results[2]["id"] == str(item1.id)
    assert results[3]["id"] == str(item2.id)
