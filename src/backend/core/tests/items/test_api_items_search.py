"""Tests for the Item viewset search method."""

import random

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_search_anonymous():
    """Anonymous users should not be able to search for items."""
    client = APIClient()
    response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 401


def test_api_items_search_authenticated_without_filters():
    """
    Authenticated users should be able to search for items.
    Without filters, all the items the user has access to should be returned.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1", type=models.ItemTypeChoices.FOLDER
    )
    top_parent_access = factories.UserItemAccessFactory(item=top_parent, user=user)
    parent = factories.ItemFactory(
        title="Item 2", parent=top_parent, type=models.ItemTypeChoices.FOLDER
    )
    children = factories.ItemFactory(
        title="Item 3", parent=parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory(title="Item hidden")

    response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 200
    assert response.data["count"] == 4

    assert response.json()["results"] == [
        {
            "abilities": user.get_main_workspace().get_abilities(user),
            "created_at": user.get_main_workspace()
            .created_at.isoformat()
            .replace("+00:00", "Z"),
            "creator": {
                "id": str(user.get_main_workspace().creator.id),
                "full_name": user.get_main_workspace().creator.full_name,
                "short_name": user.get_main_workspace().creator.short_name,
            },
            "deleted_at": None,
            "depth": 1,
            "description": None,
            "filename": None,
            "hard_delete_at": None,
            "id": str(user.get_main_workspace().id),
            "is_favorite": False,
            "link_reach": user.get_main_workspace().link_reach,
            "link_role": user.get_main_workspace().link_role,
            "main_workspace": True,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 0,
            "numchild_folder": 0,
            "parents": [],
            "path": str(user.get_main_workspace().path),
            "size": None,
            "title": "Workspace",
            "type": "folder",
            "updated_at": user.get_main_workspace()
            .updated_at.isoformat()
            .replace("+00:00", "Z"),
            "upload_state": None,
            "url": None,
            "user_roles": ["owner"],
        },
        {
            "abilities": top_parent.get_abilities(user),
            "created_at": top_parent.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(top_parent.creator.id),
                "full_name": top_parent.creator.full_name,
                "short_name": top_parent.creator.short_name,
            },
            "deleted_at": None,
            "depth": 1,
            "description": None,
            "filename": None,
            "hard_delete_at": None,
            "id": str(top_parent.id),
            "is_favorite": False,
            "link_reach": top_parent.link_reach,
            "link_role": top_parent.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 1,
            "numchild_folder": 1,
            "parents": [],
            "path": str(top_parent.path),
            "size": None,
            "title": "Item 1",
            "type": "folder",
            "updated_at": top_parent.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": None,
            "url": None,
            "user_roles": [top_parent_access.role],
        },
        {
            "abilities": parent.get_abilities(user),
            "created_at": parent.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(parent.creator.id),
                "full_name": parent.creator.full_name,
                "short_name": parent.creator.short_name,
            },
            "deleted_at": None,
            "depth": 2,
            "description": None,
            "filename": None,
            "hard_delete_at": None,
            "id": str(parent.id),
            "is_favorite": False,
            "link_reach": parent.link_reach,
            "link_role": parent.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 1,
            "numchild_folder": 0,
            "parents": [
                {
                    "abilities": top_parent.get_abilities(user),
                    "created_at": top_parent.created_at.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "creator": {
                        "id": str(top_parent.creator.id),
                        "full_name": top_parent.creator.full_name,
                        "short_name": top_parent.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 1,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(top_parent.id),
                    "is_favorite": False,
                    "link_reach": top_parent.link_reach,
                    "link_role": top_parent.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 1,
                    "numchild_folder": 1,
                    "path": str(top_parent.path),
                    "size": None,
                    "title": "Item 1",
                    "type": "folder",
                    "updated_at": top_parent.updated_at.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "upload_state": None,
                    "url": None,
                    "user_roles": [top_parent_access.role],
                }
            ],
            "path": str(parent.path),
            "size": None,
            "title": "Item 2",
            "type": "folder",
            "updated_at": parent.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": None,
            "url": None,
            "user_roles": [top_parent_access.role],
        },
        {
            "abilities": children.get_abilities(user),
            "created_at": children.created_at.isoformat().replace("+00:00", "Z"),
            "creator": {
                "id": str(children.creator.id),
                "full_name": children.creator.full_name,
                "short_name": children.creator.short_name,
            },
            "deleted_at": None,
            "depth": 3,
            "description": None,
            "filename": children.filename,
            "hard_delete_at": None,
            "id": str(children.id),
            "is_favorite": False,
            "link_reach": children.link_reach,
            "link_role": children.link_role,
            "main_workspace": False,
            "mimetype": None,
            "nb_accesses": 1,
            "numchild": 0,
            "numchild_folder": 0,
            "parents": [
                {
                    "abilities": top_parent.get_abilities(user),
                    "created_at": top_parent.created_at.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "creator": {
                        "id": str(top_parent.creator.id),
                        "full_name": top_parent.creator.full_name,
                        "short_name": top_parent.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 1,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(top_parent.id),
                    "is_favorite": False,
                    "link_reach": top_parent.link_reach,
                    "link_role": top_parent.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 1,
                    "numchild_folder": 1,
                    "path": str(top_parent.path),
                    "size": None,
                    "title": "Item 1",
                    "type": "folder",
                    "updated_at": top_parent.updated_at.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "upload_state": None,
                    "url": None,
                    "user_roles": [top_parent_access.role],
                },
                {
                    "abilities": parent.get_abilities(user),
                    "created_at": parent.created_at.isoformat().replace("+00:00", "Z"),
                    "creator": {
                        "id": str(parent.creator.id),
                        "full_name": parent.creator.full_name,
                        "short_name": parent.creator.short_name,
                    },
                    "deleted_at": None,
                    "depth": 2,
                    "description": None,
                    "filename": None,
                    "hard_delete_at": None,
                    "id": str(parent.id),
                    "is_favorite": False,
                    "link_reach": parent.link_reach,
                    "link_role": parent.link_role,
                    "main_workspace": False,
                    "mimetype": None,
                    "nb_accesses": 1,
                    "numchild": 1,
                    "numchild_folder": 0,
                    "path": str(parent.path),
                    "size": None,
                    "title": "Item 2",
                    "type": "folder",
                    "updated_at": parent.updated_at.isoformat().replace("+00:00", "Z"),
                    "upload_state": None,
                    "url": None,
                    "user_roles": [top_parent_access.role],
                },
            ],
            "path": str(children.path),
            "size": None,
            "title": "Item 3",
            "type": "file",
            "updated_at": children.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": "pending",
            "url": None,
            "user_roles": [top_parent_access.role],
        },
    ]


def test_api_items_search_authenticated_invalid_filter():
    """
    Authenticated users should be able to search for items.
    An invalid filter should return a 400 error.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1", type=models.ItemTypeChoices.FOLDER
    )
    factories.UserItemAccessFactory(item=top_parent, user=user)
    parent = factories.ItemFactory(
        title="Item 2", parent=top_parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(
        title="Item 3", parent=parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory(title="Item hidden")

    response = client.get("/api/v1.0/items/search/?type=invalid")
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "type",
                "code": "invalid",
                "detail": "Select a valid choice. invalid is not one of the available choices.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_search_authenticated_not_existing_filter():
    """
    Authenticated users should be able to search for items.
    An not existing filter should not filter at all the results.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1", type=models.ItemTypeChoices.FOLDER
    )
    factories.UserItemAccessFactory(item=top_parent, user=user)
    parent = factories.ItemFactory(
        title="Item 2", parent=top_parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(
        title="Item 3", parent=parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory(title="Item hidden")

    response = client.get("/api/v1.0/items/search/?foo=bar")
    assert response.status_code == 200
    assert response.data["count"] == 4


@pytest.mark.parametrize(
    "query,nb_results",
    [
        ("Project Alpha", 1),  # Exact match
        ("project", 2),  # Partial match (case-insensitive)
        ("Guide", 1),  # Word match within a title
        ("Special", 0),  # No match (nonexistent keyword)
        ("2024", 2),  # Match by numeric keyword
    ],
)
def test_api_items_search_authenticated_with_title_filter(query, nb_results):
    """
    Authenticated users should be able to search for items by title.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Create items with predefined titles
    titles = [
        "Project Alpha itemation",
        "Project Beta Overview",
        "User Guide",
        "Financial Report 2024",
        "Annual Review 2024",
    ]
    top_parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    non_accessible_top_parent = factories.ItemFactory(
        title="Item 3", type=models.ItemTypeChoices.FOLDER
    )
    for title in titles:
        parent = (
            factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, parent=top_parent)
            if random.choice([True, False])
            else top_parent
        )
        factories.ItemFactory(title=title, parent=parent)
        factories.ItemFactory(title=title, parent=non_accessible_top_parent)

    response = client.get(f"/api/v1.0/items/search/?title={query:s}")
    assert response.status_code == 200
    assert response.data["count"] == nb_results


def test_api_items_search_authenticated_by_type():
    """
    Authenticated users should be able to search for items by type.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=top_parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory.create_batch(
        3, parent=top_parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=user.get_main_workspace(), type=models.ItemTypeChoices.FILE
    )

    response = client.get("/api/v1.0/items/search/?type=file")
    assert response.status_code == 200
    assert response.data["count"] == 6

    response = client.get("/api/v1.0/items/search/?type=folder")
    assert response.status_code == 200
    assert (
        response.data["count"] == 3
    )  # top_parent and user.get_main_workspace() are removed.

    response = client.get("/api/v1.0/items/search/?type=workspace")
    assert response.status_code == 200
    assert (
        response.data["count"] == 2
    )  # top_parent and user.get_main_workspace() are workspaces.


def test_api_items_search_authenticated_by_workspace():
    """
    Authenticated users should be able to search for items by workspace.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=parent, type=models.ItemTypeChoices.FILE
    )
    factories.ItemFactory.create_batch(
        3, parent=parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=user.get_main_workspace(), type=models.ItemTypeChoices.FILE
    )

    response = client.get(f"/api/v1.0/items/search/?workspace={parent.id}")
    assert response.status_code == 200
    assert response.data["count"] == 7  # 6 children + 1 parent

    response = client.get(
        f"/api/v1.0/items/search/?workspace={user.get_main_workspace().id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == 4  # 3 children + 1 parent


def test_api_items_search_authenticated_combined_filters():
    """
    Authenticated users should be able to search for items by combining multiple filters.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parents = factories.ItemFactory.create_batch(
        3, users=[user], type=models.ItemTypeChoices.FOLDER
    )
    # Create items with predefined titles
    titles = [
        "Project Alpha itemation",
        "Project Beta Overview",
        "User Guide",
        "Financial Report 2024",
        "Annual Review 2024",
    ]
    parent_childrens = {parent.id: [] for parent in parents}
    for title in titles:
        parent = random.choice(parents)
        children = factories.ItemFactory(
            title=title, parent=parent, type=models.ItemTypeChoices.FILE
        )
        factories.ItemFactory(
            title=title,
            parent=user.get_main_workspace(),
            type=models.ItemTypeChoices.FILE,
        )
        parent_childrens[parent.id].append(children)

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={parents[0].id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == len(parent_childrens[parents[0].id])

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={parents[1].id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == len(parent_childrens[parents[1].id])

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={parents[2].id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == len(parent_childrens[parents[2].id])

    response = client.get(
        f"/api/v1.0/items/search/?type=file&workspace={user.get_main_workspace().id}&title=Project"
    )
    assert response.status_code == 200
    assert response.data["count"] == 2


def test_api_items_search_authenticated_filter_with_unaccessibile_workspace():
    """
    Authenticated users should not be able to search for items in unaccessible workspaces.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    unaccessible_workspace = factories.ItemFactory(
        title="Item 1", type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=unaccessible_workspace, type=models.ItemTypeChoices.FILE
    )

    response = client.get(
        f"/api/v1.0/items/search/?workspace={unaccessible_workspace.id}"
    )
    assert response.status_code == 200
    assert response.data["count"] == 0


def test_api_items_search_authenticated_filter_with_workspace_children():
    """
    Authenticated users should not be able to filter using a folder with depth > 1
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        title="Item 1", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    children = factories.ItemFactory(
        title="Item 2", parent=parent, type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=children, type=models.ItemTypeChoices.FILE
    )

    response = client.get(f"/api/v1.0/items/search/?workspace={parent.id}&type=file")
    assert response.status_code == 200
    assert response.data["count"] == 3

    response = client.get(f"/api/v1.0/items/search/?workspace={children.id}")
    assert response.status_code == 200
    assert response.data["count"] == 0
