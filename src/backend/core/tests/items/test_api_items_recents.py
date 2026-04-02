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
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    child_item_file = factories.ItemFactory(
        creator=user,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="child file",
        update_upload_state=models.ItemUploadStateChoices.READY,
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
        update_upload_state=models.ItemUploadStateChoices.READY,
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

    # delete other_items 2, should not be in the results
    other_items[2].soft_delete()

    client = APIClient()
    client.force_login(user)

    with django_assert_num_queries(7):
        response = client.get("/api/v1.0/items/recents/")
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 7
    assert content["results"][0]["id"] == str(other_items[0].id)
    assert content["results"][1]["id"] == str(items[0].id)
    assert content["results"][2]["id"] == str(parent.id)
    assert content["results"][3]["id"] == str(other_items[1].id)
    assert content["results"][4]["id"] == str(other_parent.id)
    assert content["results"][5]["id"] == str(items[2].id)
    assert content["results"][6]["id"] == str(items[1].id)


def test_api_items_recents_filtering(django_assert_num_queries):
    """
    Test filtering the recents items by type.
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

    # delete other_items 2, should not be in the results
    other_items[2].soft_delete()

    client = APIClient()
    client.force_login(user)

    with django_assert_num_queries(7):
        response = client.get("/api/v1.0/items/recents/?type=folder")

    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 2
    assert content["results"][0]["id"] == str(parent.id)
    assert content["results"][1]["id"] == str(other_parent.id)

    with django_assert_num_queries(7):
        response = client.get("/api/v1.0/items/recents/?type=file")

    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 5
    assert content["results"][0]["id"] == str(other_items[0].id)
    assert content["results"][1]["id"] == str(items[0].id)
    assert content["results"][2]["id"] == str(other_items[1].id)
    assert content["results"][3]["id"] == str(items[2].id)
    assert content["results"][4]["id"] == str(items[1].id)


def test_api_item_recents_excludes_pending_items():
    """Items with upload_state=PENDING should be excluded from recents."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(item=parent, user=user, role="editor")

    # Should be visible
    ready_file = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    # Should not be visible
    pending_file = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
    )

    response = client.get("/api/v1.0/items/recents/")

    assert response.status_code == 200
    result_ids = [r["id"] for r in response.json()["results"]]
    assert str(ready_file.id) in result_ids
    assert str(pending_file.id) not in result_ids


@pytest.mark.parametrize(
    "ordering",
    [
        "created_at",
        "-created_at",
        "title",
        "-title",
        "updated_at",
        "-updated_at",
    ],
)
def test_api_item_recents_ordering_by_fields(ordering, django_assert_num_queries):
    """Test ordering the recents endpoint by fields"""

    user1 = factories.UserFactory(full_name="Camille Clement", short_name="camille")
    user2 = factories.UserFactory(full_name="Eva Roussel", short_name="Eva")

    parent_item = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="aaaa",
    )
    child_item = factories.ItemFactory(
        creator=user1,
        parent=parent_item,
        type=models.ItemTypeChoices.FOLDER,
        title="bbbb",
    )
    child_item_child = factories.ItemFactory(
        creator=user1,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="cccc",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=10,
    )
    child_item_file = factories.ItemFactory(
        creator=user2,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="dddd",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=20,
    )

    parent2_item = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="eeee",
    )
    child2_item_file = factories.ItemFactory(
        creator=user2,
        parent=parent2_item,
        type=models.ItemTypeChoices.FILE,
        title="ffff",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=30,
    )

    client = APIClient()
    client.force_login(user1)

    is_descending = ordering.startswith("-")
    querystring = f"?ordering={ordering}"

    with django_assert_num_queries(7):
        response = client.get(f"/api/v1.0/items/recents/{querystring:s}")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 6

    if is_descending:
        assert results[0]["id"] == str(child2_item_file.id)
        assert results[1]["id"] == str(parent2_item.id)
        assert results[2]["id"] == str(child_item_file.id)
        assert results[3]["id"] == str(child_item_child.id)
        assert results[4]["id"] == str(child_item.id)
        assert results[5]["id"] == str(parent_item.id)
    else:
        assert results[0]["id"] == str(parent_item.id)
        assert results[1]["id"] == str(child_item.id)
        assert results[2]["id"] == str(child_item_child.id)
        assert results[3]["id"] == str(child_item_file.id)
        assert results[4]["id"] == str(parent2_item.id)
        assert results[5]["id"] == str(child2_item_file.id)


@pytest.mark.parametrize(
    "ordering",
    [
        "size",
        "-size",
    ],
)
def test_api_item_recents_ordering_by_size(ordering, django_assert_num_queries):
    """Test ordering the recents endpoint by size"""

    user1 = factories.UserFactory(full_name="Camille Clement", short_name="camille")
    user2 = factories.UserFactory(full_name="Eva Roussel", short_name="Eva")

    parent_item = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="aaaa",
    )
    child_item = factories.ItemFactory(
        creator=user1,
        parent=parent_item,
        type=models.ItemTypeChoices.FOLDER,
        title="bbbb",
    )
    child_item_child = factories.ItemFactory(
        creator=user1,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="cccc",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=10,
    )
    child_item_file = factories.ItemFactory(
        creator=user2,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="dddd",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=20,
    )

    parent2_item = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="eeee",
    )
    child2_item_file = factories.ItemFactory(
        creator=user2,
        parent=parent2_item,
        type=models.ItemTypeChoices.FILE,
        title="ffff",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=30,
    )

    client = APIClient()
    client.force_login(user1)

    is_descending = ordering.startswith("-")
    querystring = f"?ordering={ordering}"

    with django_assert_num_queries(7):
        response = client.get(f"/api/v1.0/items/recents/{querystring:s}")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 6

    if is_descending:
        assert results[0]["id"] == str(parent2_item.id)
        assert results[1]["id"] == str(child_item.id)
        assert results[2]["id"] == str(parent_item.id)
        assert results[3]["id"] == str(child2_item_file.id)
        assert results[4]["id"] == str(child_item_file.id)
        assert results[5]["id"] == str(child_item_child.id)
    else:
        assert results[0]["id"] == str(child_item_child.id)
        assert results[1]["id"] == str(child_item_file.id)
        assert results[2]["id"] == str(child2_item_file.id)
        assert results[3]["id"] == str(parent2_item.id)
        assert results[4]["id"] == str(child_item.id)
        assert results[5]["id"] == str(parent_item.id)


@pytest.mark.parametrize(
    "ordering",
    [
        "creator__full_name",
        "-creator__full_name",
    ],
)
def test_api_item_recents_ordering_by_creator_full_name(ordering, django_assert_num_queries):
    """Test ordering the recents list endpoint by creator full name"""

    user1 = factories.UserFactory(full_name="Camille Clement", short_name="camille")
    user2 = factories.UserFactory(full_name="Eva Roussel", short_name="Eva")

    parent_item = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="aaaa",
    )
    child_item = factories.ItemFactory(
        creator=user1,
        parent=parent_item,
        type=models.ItemTypeChoices.FOLDER,
        title="bbbb",
    )
    child_item_child = factories.ItemFactory(
        creator=user1,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="cccc",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=10,
    )
    child_item_file = factories.ItemFactory(
        creator=user2,
        parent=child_item,
        type=models.ItemTypeChoices.FILE,
        title="dddd",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=20,
    )

    parent2_item = factories.ItemFactory(
        creator=user1,
        users=[(user1, "owner"), (user2, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="eeee",
    )
    child2_item_file = factories.ItemFactory(
        creator=user2,
        parent=parent2_item,
        type=models.ItemTypeChoices.FILE,
        title="ffff",
        update_upload_state=models.ItemUploadStateChoices.READY,
        size=30,
    )

    client = APIClient()
    client.force_login(user1)

    is_descending = ordering.startswith("-")
    querystring = f"?ordering={ordering}"

    with django_assert_num_queries(7):
        response = client.get(f"/api/v1.0/items/recents/{querystring:s}")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 6

    if is_descending:
        assert results[0]["id"] == str(child2_item_file.id)
        assert results[1]["id"] == str(child_item_file.id)
        assert results[2]["id"] == str(parent2_item.id)
        assert results[3]["id"] == str(child_item_child.id)
        assert results[4]["id"] == str(child_item.id)
        assert results[5]["id"] == str(parent_item.id)

    else:
        assert results[0]["id"] == str(parent2_item.id)
        assert results[1]["id"] == str(child_item_child.id)
        assert results[2]["id"] == str(child_item.id)
        assert results[3]["id"] == str(parent_item.id)
        assert results[4]["id"] == str(child2_item_file.id)
        assert results[5]["id"] == str(child_item_file.id)
