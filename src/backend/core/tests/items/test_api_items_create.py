"""
Tests for items API endpoint in drive's core app: create
"""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from django.conf import settings

import pytest
from rest_framework.test import APIClient

from core import factories
from core.models import Item, ItemTypeChoices

pytestmark = pytest.mark.django_db


def test_api_items_create_anonymous():
    """Anonymous users should not be allowed to create items."""
    response = APIClient().post(
        "/api/v1.0/items/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
    )

    assert response.status_code == 401
    assert not Item.objects.exists()


def test_api_items_create_authenticated_success():
    """
    Authenticated users should be able to create items and should automatically be declared
    as the owner of the newly created item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )
    assert response.status_code == 201
    item = Item.objects.exclude(id=user.get_main_workspace().id).get()
    assert item.title == "my item"
    assert item.link_reach == "restricted"
    assert item.accesses.filter(role="owner", user=user).exists()
    assert item.type == ItemTypeChoices.FOLDER


def test_api_items_create_file_authenticated_no_filename():
    """
    Creating a file item without providing a filename should fail.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "filename",
                "code": "item_create_file_filename_required",
                "detail": "This field is required for files.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_file_authenticated_success():
    """
    Authenticated users should be able to create a file item and must provide a filename.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/",
        {
            "type": ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
        format="json",
    )
    assert response.status_code == 201
    item = Item.objects.exclude(id=user.get_main_workspace().id).get()
    assert item.title == "file.txt"
    assert item.link_reach == "restricted"
    assert item.accesses.filter(role="owner", user=user).exists()
    assert item.type == ItemTypeChoices.FILE
    assert item.filename == "file.txt"

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
            "key": f"item/{item.id!s}/file.txt",
            "AWSAccessKeyId": "drive",
        },
    }


def test_api_items_create_authenticated_title_null():
    """It should not be possible to create several items with a null title."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/items/", {"type": ItemTypeChoices.FOLDER}, format="json"
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "title",
                "code": "item_create_folder_title_required",
                "detail": "This field is required for folders.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_create_force_id_success():
    """It should be possible to force the item ID when creating a   item."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    forced_id = uuid4()

    response = client.post(
        "/api/v1.0/items/",
        {
            "id": str(forced_id),
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )

    assert response.status_code == 201
    items = Item.objects.all().exclude(id=user.get_main_workspace().id)
    assert len(items) == 1
    assert items[0].id == forced_id


def test_api_items_create_force_id_existing():
    """
    It should not be possible to use the ID of an existing item when forcing ID on creation.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()

    response = client.post(
        "/api/v1.0/items/",
        {
            "id": str(item.id),
            "title": "my item",
            "type": ItemTypeChoices.FOLDER,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "id",
                "code": "item_create_existing_id",
                "detail": "An item with this ID already exists. You cannot override it.",
            },
        ],
        "type": "validation_error",
    }


@pytest.mark.django_db(transaction=True)
def test_api_items_create_item_race_condition():
    """
    It should be possible to create several items at the same time
    without causing any race conditions or data integrity issues.
    """

    def create_item(title):
        user = factories.UserFactory()
        client = APIClient()
        client.force_login(user)
        return client.post(
            "/api/v1.0/items/",
            {
                "title": title,
                "type": ItemTypeChoices.FOLDER,
            },
            format="json",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(create_item, "my item 1")
        future2 = executor.submit(create_item, "my item 2")

        response1 = future1.result()
        response2 = future2.result()

        assert response1.status_code == 201
        assert response2.status_code == 201
