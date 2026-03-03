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

    item2.upload_state = models.ItemUploadStateChoices.READY
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

    item2.upload_state = models.ItemUploadStateChoices.READY
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


def test_api_items_children_ordering_size():
    """Validate the ordering of children items by size."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)
    item_small = factories.ItemFactory(
        parent=root,
        users=[user],
        title="small_file",
        type=models.ItemTypeChoices.FILE,
        size=100,
    )
    item_large = factories.ItemFactory(
        parent=root,
        users=[user],
        title="large_file",
        type=models.ItemTypeChoices.FILE,
        size=999999,
    )
    item_no_size = factories.ItemFactory(
        parent=root,
        users=[user],
        title="folder_no_size",
        type=models.ItemTypeChoices.FOLDER,
        size=None,
    )

    # Ascending: small, large, then nulls last (PostgreSQL default)
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=size")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["id"] == str(item_small.id)
    assert results[1]["id"] == str(item_large.id)
    assert results[2]["id"] == str(item_no_size.id)

    # Descending: nulls first (PostgreSQL default), then large, then small
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=-size")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["id"] == str(item_no_size.id)
    assert results[1]["id"] == str(item_large.id)
    assert results[2]["id"] == str(item_small.id)


def test_api_items_children_ordering_creator():
    """Validate the ordering of children items by creator full name."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    creator_a = factories.UserFactory(full_name="Alice")
    creator_z = factories.UserFactory(full_name="Zara")

    root = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)
    item_a = factories.ItemFactory(
        parent=root,
        users=[user],
        title="item_by_alice",
        type=models.ItemTypeChoices.FOLDER,
        creator=creator_a,
    )
    item_z = factories.ItemFactory(
        parent=root,
        users=[user],
        title="item_by_zara",
        type=models.ItemTypeChoices.FOLDER,
        creator=creator_z,
    )

    # Ascending: Alice before Zara
    response = client.get(
        f"/api/v1.0/items/{root.id}/children/?ordering=creator__full_name"
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_a.id)
    assert results[1]["id"] == str(item_z.id)

    # Descending: Zara before Alice
    response = client.get(
        f"/api/v1.0/items/{root.id}/children/?ordering=-creator__full_name"
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["id"] == str(item_z.id)
    assert results[1]["id"] == str(item_a.id)


def test_api_items_children_ordering_mime_category():
    """Validate that ordering by mime_category groups items by display category."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(users=[user], type=models.ItemTypeChoices.FOLDER)

    item_pdf = factories.ItemFactory(
        parent=root,
        users=[user],
        title="doc.pdf",
        type=models.ItemTypeChoices.FILE,
        mimetype="application/pdf",
    )
    item_image = factories.ItemFactory(
        parent=root,
        users=[user],
        title="photo.png",
        type=models.ItemTypeChoices.FILE,
        mimetype="image/png",
    )
    item_svg = factories.ItemFactory(
        parent=root,
        users=[user],
        title="logo.svg",
        type=models.ItemTypeChoices.FILE,
        mimetype="image/svg+xml",
    )
    item_other = factories.ItemFactory(
        parent=root,
        users=[user],
        title="notes.md",
        type=models.ItemTypeChoices.FILE,
        mimetype="text/markdown",
    )
    item_folder = factories.ItemFactory(
        parent=root,
        users=[user],
        title="My Folder",
        type=models.ItemTypeChoices.FOLDER,
    )

    # Ascending: categories alphabetically → folder, image, other, pdf
    response = client.get(f"/api/v1.0/items/{root.id}/children/?ordering=mime_category")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 5

    result_ids = [r["id"] for r in results]

    # folder < image < other < pdf (alphabetical)
    assert result_ids.index(str(item_folder.id)) < result_ids.index(str(item_image.id))
    assert result_ids.index(str(item_image.id)) < result_ids.index(str(item_other.id))
    assert result_ids.index(str(item_other.id)) < result_ids.index(str(item_pdf.id))

    # Both images should be next to each other
    image_positions = [
        result_ids.index(str(item_image.id)),
        result_ids.index(str(item_svg.id)),
    ]
    assert abs(image_positions[0] - image_positions[1]) == 1

    # Descending: pdf, other, image, folder
    response = client.get(
        f"/api/v1.0/items/{root.id}/children/?ordering=-mime_category"
    )
    assert response.status_code == 200
    results = response.json()["results"]
    result_ids = [r["id"] for r in results]

    assert result_ids.index(str(item_pdf.id)) < result_ids.index(str(item_other.id))
    assert result_ids.index(str(item_other.id)) < result_ids.index(str(item_image.id))
    assert result_ids.index(str(item_image.id)) < result_ids.index(str(item_folder.id))


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
