"""Test for the document favorite_list endpoint."""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_item_favorite_list_anonymous():
    """Anonymous users should receive a 401 error."""

    client = APIClient()

    response = client.get("/api/v1.0/items/favorite_list/")

    assert response.status_code == 401


def test_api_item_favorite_list_authenticated_no_favorite():
    """Authenticated users should receive an empty list."""

    user = factories.UserFactory()

    client = APIClient()

    client.force_login(user)

    response = client.get("/api/v1.0/items/favorite_list/")

    assert response.status_code == 200

    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_api_item_favorite_list_authenticated_with_favorite():
    """Authenticated users with a favorite should receive the favorite."""

    user = factories.UserFactory()

    client = APIClient()

    client.force_login(user)

    # User don't have access to this item, let say it had access and this access has been
    # removed. It should not be in the favorite list anymore.
    factories.ItemFactory(favorited_by=[user])

    item = factories.UserItemAccessFactory(
        user=user, role=models.RoleChoices.READER, item__favorited_by=[user]
    ).item

    response = client.get("/api/v1.0/items/favorite_list/")

    assert response.status_code == 200

    assert response.json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": item.get_abilities(user),
                "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(item.creator.id),
                    "full_name": item.creator.full_name,
                    "short_name": item.creator.short_name,
                },
                "depth": item.depth,
                "id": str(item.id),
                "link_reach": item.link_reach,
                "link_role": item.link_role,
                "nb_accesses": item.nb_accesses,
                "numchild": item.numchild,
                "numchild_folder": item.numchild_folder,
                "path": str(item.path),
                "title": item.title,
                "type": item.type,
                "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
                "upload_state": item.upload_state,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "user_role": "reader",
                "main_workspace": False,
                "filename": item.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            }
        ],
    }


def test_api_item_favorite_list_with_suspicious_items():
    """
    Suspicious items should not be listed in favorite list for non creator.
    """
    creator = factories.UserFactory()
    other_user = factories.UserFactory()
    client = APIClient()
    client.force_login(other_user)

    # Create suspicious item and mark it as favorite by non-creator
    suspicious_item = factories.ItemFactory(
        creator=creator,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[creator, other_user],
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
        favorited_by=[other_user, creator],
    )

    # Create normal item and mark it as favorite by non-creator
    normal_item = factories.ItemFactory(
        creator=creator,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[creator, other_user],
        type=models.ItemTypeChoices.FILE,
        filename="normal.txt",
        favorited_by=[other_user, creator],
    )

    # Non-creator should only see normal item in favorite list, not suspicious one
    response = client.get("/api/v1.0/items/favorite_list/")
    assert response.status_code == 200
    content = response.json()

    # Should only see 1 normal item, not the suspicious one
    assert content["count"] == 1
    item_ids = [item["id"] for item in content["results"]]
    assert str(suspicious_item.id) not in item_ids
    assert str(normal_item.id) in item_ids

    # Creator should see all their favorited items including suspicious one
    client.force_login(creator)
    response = client.get("/api/v1.0/items/favorite_list/")
    assert response.status_code == 200
    content = response.json()

    assert content["count"] == 2
    item_ids = [item["id"] for item in content["results"]]
    assert str(suspicious_item.id) in item_ids
    assert str(normal_item.id) in item_ids
