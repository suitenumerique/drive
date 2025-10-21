"""Tests for the Item viewset search method with fulltext."""

import pytest
import responses
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("indexer_settings")
@responses.activate
def test_api_items_search_authenticated_fulltext_query(indexer_settings):
    """
    Authenticated users should be able to search for items by title.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    indexer_settings.SEARCH_INDEXER_QUERY_URL = "http://find/api/v1.0/search"

    # Create items with predefined titles
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder_access = factories.UserItemAccessFactory(item=folder, user=user)
    _, item_b, item_c = factories.ItemFactory.create_batch(
        3, parent=folder, type=models.ItemTypeChoices.FILE
    )

    # Find response
    responses.add(
        responses.POST,
        "http://find/api/v1.0/search",
        json=[
            {"_id": str(item_b.pk)},
            {"_id": str(item_c.pk)},
        ],
        status=200,
    )

    response = client.get("/api/v1.0/items/search/?title=alpha")
    assert response.status_code == 200
    assert response.data["count"] == 2

    assert response.json()["results"] == [
        {
            "abilities": item_b.get_abilities(user),
            "created_at": item_b.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(item_b.creator.id),
                "full_name": item_b.creator.full_name,
                "short_name": item_b.creator.short_name,
            },
            "deleted_at": None,
            "depth": 2,
            "description": None,
            "filename": item_b.filename,
            "hard_delete_at": None,
            "id": str(item_b.id),
            "is_favorite": False,
            "is_wopi_supported": False,
            "link_reach": item_b.link_reach,
            "link_role": item_b.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 0,
            "numchild_folder": 0,
            "path": str(item_b.path),
            "size": None,
            "title": item_b.title,
            "type": "file",
            "updated_at": item_b.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": str(item_b.upload_state),
            "url": None,
            "url_preview": None,
            "user_roles": [folder_access.role],
            "parents": [
                {
                    "abilities": folder.get_abilities(user),
                    "created_at": folder.created_at.isoformat().replace("+00:00", "Z"),
                    "creator": {
                        "id": str(folder.creator.id),
                        "full_name": folder.creator.full_name,
                        "short_name": folder.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 1,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(folder.id),
                    "is_wopi_supported": False,
                    "link_reach": folder.link_reach,
                    "link_role": folder.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 3,
                    "numchild_folder": 0,
                    "path": str(folder.path),
                    "size": None,
                    "title": folder.title,
                    "type": "folder",
                    "updated_at": folder.updated_at.isoformat().replace("+00:00", "Z"),
                    "upload_state": None,
                    "url": None,
                    "url_preview": None,
                    "user_roles": [folder_access.role],
                },
            ],
        },
        {
            "abilities": item_c.get_abilities(user),
            "created_at": item_c.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(item_c.creator.id),
                "full_name": item_c.creator.full_name,
                "short_name": item_c.creator.short_name,
            },
            "deleted_at": None,
            "depth": 2,
            "description": None,
            "filename": item_c.filename,
            "hard_delete_at": None,
            "id": str(item_c.id),
            "is_favorite": False,
            "is_wopi_supported": False,
            "link_reach": item_c.link_reach,
            "link_role": item_c.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 0,
            "numchild_folder": 0,
            "path": str(item_c.path),
            "size": None,
            "title": item_c.title,
            "type": "file",
            "updated_at": item_c.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": str(item_c.upload_state),
            "url": None,
            "url_preview": None,
            "user_roles": [folder_access.role],
            "parents": [
                {
                    "abilities": folder.get_abilities(user),
                    "created_at": folder.created_at.isoformat().replace("+00:00", "Z"),
                    "creator": {
                        "id": str(folder.creator.id),
                        "full_name": folder.creator.full_name,
                        "short_name": folder.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 1,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(folder.id),
                    "is_wopi_supported": False,
                    "link_reach": folder.link_reach,
                    "link_role": folder.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 3,
                    "numchild_folder": 0,
                    "path": str(folder.path),
                    "size": None,
                    "title": folder.title,
                    "type": "folder",
                    "updated_at": folder.updated_at.isoformat().replace("+00:00", "Z"),
                    "upload_state": None,
                    "url": None,
                    "url_preview": None,
                    "user_roles": [folder_access.role],
                },
            ],
        },
    ]
