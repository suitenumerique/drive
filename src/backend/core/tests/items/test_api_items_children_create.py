"""
Tests for items API endpoint in drive's core app: create
"""

from concurrent.futures import ThreadPoolExecutor
from random import randint
from uuid import uuid4

from django.conf import settings

import pytest
from rest_framework.test import APIClient

from core import factories
from core.models import Item, ItemTypeChoices, LinkReachChoices, LinkRoleChoices

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize("role", LinkRoleChoices.values)
@pytest.mark.parametrize("reach", LinkReachChoices.values)
def test_api_items_children_create_anonymous(reach, role, depth):
    """Anonymous users should not be allowed to create children items."""
    for i in range(depth):
        if i == 0:
            item = factories.ItemFactory(
                link_reach=reach, link_role=role, type=ItemTypeChoices.FOLDER
            )
        else:
            item = factories.ItemFactory(parent=item, type=ItemTypeChoices.FOLDER)

    items_created = Item.objects.all().count()

    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FILE,
        },
    )

    assert Item.objects.count() == items_created
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize(
    "reach,role",
    [
        ["restricted", "editor"],
        ["restricted", "reader"],
        ["public", "reader"],
        ["authenticated", "reader"],
    ],
)
def test_api_items_children_create_authenticated_forbidden(reach, role, depth):
    """
    Authenticated users with no write access on a item should not be allowed
    to create a nested item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    for i in range(depth):
        if i == 0:
            item = factories.ItemFactory(
                link_reach=reach, link_role=role, type=ItemTypeChoices.FOLDER
            )
        else:
            item = factories.ItemFactory(
                parent=item, link_role="reader", type=ItemTypeChoices.FOLDER
            )

    items_created = Item.objects.all().count()
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FILE,
        },
    )

    assert response.status_code == 403
    assert Item.objects.count() == items_created


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize(
    "reach,role",
    [
        ["public", "editor"],
        ["authenticated", "editor"],
    ],
)
def test_api_items_children_create_authenticated_success(reach, role, depth):
    """
    Authenticated users with write access on an item should be able
    to create a nested item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    for i in range(depth):
        if i == 0:
            item = factories.ItemFactory(
                link_reach=reach, link_role=role, type=ItemTypeChoices.FOLDER
            )
        else:
            item = factories.ItemFactory(
                parent=item, link_role="reader", type=ItemTypeChoices.FOLDER
            )

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
    )

    assert response.status_code == 201

    child = Item.objects.get(id=response.json()["id"])
    assert child.title == "file.txt"
    assert child.link_reach == "restricted"
    assert not child.accesses.filter(role="owner", user=user).exists()


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_api_items_children_create_related_forbidden(depth):
    """
    Authenticated users with a specific read access on an item should not be allowed
    to create a nested item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    for i in range(depth):
        if i == 0:
            item = factories.ItemFactory(
                link_reach="restricted", type=ItemTypeChoices.FOLDER
            )
            factories.UserItemAccessFactory(user=user, item=item, role="reader")
        else:
            item = factories.ItemFactory(
                parent=item, link_reach="restricted", type=ItemTypeChoices.FOLDER
            )

    items_created = Item.objects.all().count()
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FILE,
        },
    )

    assert response.status_code == 403
    assert Item.objects.count() == items_created


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize("role", ["editor", "administrator", "owner"])
def test_api_items_children_create_related_success(role, depth):
    """
    Authenticated users with a specific write access on a item should be
    able to create a nested item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    for i in range(depth):
        if i == 0:
            item = factories.ItemFactory(
                link_reach="restricted", type=ItemTypeChoices.FOLDER
            )
            factories.UserItemAccessFactory(user=user, item=item, role=role)
        else:
            item = factories.ItemFactory(
                parent=item, link_reach="restricted", type=ItemTypeChoices.FOLDER
            )

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
    )

    assert response.status_code == 201
    child = Item.objects.get(id=response.json()["id"])
    assert child.title == "file.txt"
    assert child.link_reach == "restricted"
    assert not child.accesses.filter(role="owner", user=user).exists()

    assert response.json().get("policy") is not None

    policy = response.json()["policy"]
    assert policy.get("fields").get("policy") is not None
    assert policy.get("fields").get("signature") is not None
    del policy["fields"]["policy"]
    del policy["fields"]["signature"]

    assert policy == {
        "url": f"{settings.AWS_S3_ENDPOINT_URL}/drive-media-storage",
        "fields": {
            "acl": "private",
            "key": f"item/{child.id!s}/file.txt",
            "AWSAccessKeyId": "drive",
        },
    }


def test_api_items_children_create_force_id_success():
    """It should be possible to force the item ID when creating a nested item."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="editor", item__type=ItemTypeChoices.FOLDER
    )
    forced_id = uuid4()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "id": str(forced_id),
            "title": "my item",
            "type": ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(forced_id)


def test_api_items_children_create_force_id_existing():
    """
    It should not be possible to use the ID of an existing item when forcing ID on creation.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="editor", item__type=ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "id": str(item.id),
            "title": "my item",
            "type": ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "id": ["An item with this ID already exists. You cannot override it."]
    }


def test_api_items_children_create_title_already_existing_at_the_same_level():
    """
    It should not be possible to create a nested item with a title that already exists
    at the same level.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="editor", item__type=ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(
        parent=access.item, title="my item", type=ItemTypeChoices.FOLDER
    )

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {"title": ["title already exists in this folder."]}


def test_api_items_children_create_item_soft_deleted_with_same_title_exists():
    """
    It should be possible to create a new nested item with the same title as a soft-deleted item.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory(
        user=user, role="editor", item__type=ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(
        parent=access.item, title="my item", type=ItemTypeChoices.FOLDER
    )
    item.soft_delete()

    response = client.post(
        f"/api/v1.0/items/{access.item.id!s}/children/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["title"] == "my item"
    assert response.json()["type"] == ItemTypeChoices.FOLDER.value


@pytest.mark.django_db(transaction=True)
def test_api_items_create_item_children_race_condition():
    """
    It should be possible to create several items at the same time
    without causing any race conditions or data integrity issues.
    """

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=ItemTypeChoices.FOLDER)

    factories.UserItemAccessFactory(user=user, item=item, role="owner")

    def create_item():
        return client.post(
            f"/api/v1.0/items/{item.id}/children/",
            {
                "title": f"my child {randint(1, 1000)}",
                "type": ItemTypeChoices.FOLDER,
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(create_item)
        future2 = executor.submit(create_item)

        response1 = future1.result()
        response2 = future2.result()

        assert response1.status_code == 201
        assert response2.status_code == 201

        item.refresh_from_db()
        assert item.numchild == 2
