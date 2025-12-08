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
    deleted_file = factories.ItemFactory(
        title="Deleted file", type=models.ItemTypeChoices.FILE, parent=top_parent
    )
    deleted_file.soft_delete()

    response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 200
    assert response.data["count"] == 3

    assert response.json()["results"] == [
        {
            "abilities": top_parent.get_abilities(user),
            "ancestors_link_reach": None,
            "ancestors_link_role": None,
            "computed_link_reach": top_parent.computed_link_reach,
            "computed_link_role": top_parent.computed_link_role,
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
            "is_wopi_supported": False,
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
            "url_preview": None,
            "user_role": top_parent_access.role,
        },
        {
            "abilities": parent.get_abilities(user),
            "ancestors_link_reach": parent.ancestors_link_reach,
            "ancestors_link_role": parent.ancestors_link_role,
            "computed_link_reach": parent.computed_link_reach,
            "computed_link_role": parent.computed_link_role,
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
            "is_wopi_supported": False,
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
                    "ancestors_link_reach": top_parent.ancestors_link_reach,
                    "ancestors_link_role": top_parent.ancestors_link_role,
                    "computed_link_reach": top_parent.computed_link_reach,
                    "computed_link_role": top_parent.computed_link_role,
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
                    "is_wopi_supported": False,
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
                    "url_preview": None,
                    "user_role": top_parent_access.role,
                }
            ],
            "path": str(parent.path),
            "size": None,
            "title": "Item 2",
            "type": "folder",
            "updated_at": parent.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": None,
            "url": None,
            "url_preview": None,
            "user_role": top_parent_access.role,
        },
        {
            "abilities": children.get_abilities(user),
            "ancestors_link_reach": children.ancestors_link_reach,
            "ancestors_link_role": children.ancestors_link_role,
            "computed_link_reach": children.computed_link_reach,
            "computed_link_role": children.computed_link_role,
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
            "is_wopi_supported": False,
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
                    "ancestors_link_reach": top_parent.ancestors_link_reach,
                    "ancestors_link_role": top_parent.ancestors_link_role,
                    "computed_link_reach": top_parent.computed_link_reach,
                    "computed_link_role": top_parent.computed_link_role,
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
                    "is_wopi_supported": False,
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
                    "url_preview": None,
                    "user_role": top_parent_access.role,
                },
                {
                    "abilities": parent.get_abilities(user),
                    "ancestors_link_reach": parent.ancestors_link_reach,
                    "ancestors_link_role": parent.ancestors_link_role,
                    "computed_link_reach": parent.computed_link_reach,
                    "computed_link_role": parent.computed_link_role,
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
                    "is_wopi_supported": False,
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
                    "url_preview": None,
                    "user_role": top_parent_access.role,
                },
            ],
            "path": str(children.path),
            "size": None,
            "title": "Item 3",
            "type": "file",
            "updated_at": children.updated_at.isoformat().replace("+00:00", "Z"),
            "upload_state": "pending",
            "url": None,
            "url_preview": None,
            "user_role": top_parent_access.role,
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
    assert response.data["count"] == 3


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
    other_top_parent = factories.ItemFactory(
        title="Item 2", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=other_top_parent, type=models.ItemTypeChoices.FILE
    )

    deleted_file = factories.ItemFactory(
        title="Deleted file", type=models.ItemTypeChoices.FILE, parent=top_parent
    )
    deleted_file.soft_delete()

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


def test_api_items_search_authenticated_filter_scopes():
    """
    Authenticated users should be able to search for items by deleted status.
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
    other_top_parent = factories.ItemFactory(
        title="Item 2", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=other_top_parent, type=models.ItemTypeChoices.FILE
    )

    deleted_file = factories.ItemFactory(
        title="Deleted file", type=models.ItemTypeChoices.FILE, parent=top_parent
    )
    deleted_file.soft_delete()

    response = client.get("/api/v1.0/items/search/")
    assert response.status_code == 200
    assert response.data["count"] == 11

    response = client.get("/api/v1.0/items/search/?scope=all")
    assert response.status_code == 200
    assert response.data["count"] == 12

    response = client.get("/api/v1.0/items/search/?scope=deleted")
    assert response.status_code == 200
    assert response.data["count"] == 1

    response = client.get("/api/v1.0/items/search/?scope=not_deleted")
    assert response.status_code == 200
    assert response.data["count"] == 11

    response = client.get("/api/v1.0/items/search/?scope=deleted&scope=not_deleted")
    assert response.status_code == 200
    assert response.data["count"] == 12


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
    other_top_parent = factories.ItemFactory(
        title="Item 2", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(
        3, parent=other_top_parent, type=models.ItemTypeChoices.FILE
    )

    response = client.get(f"/api/v1.0/items/search/?workspace={parent.id}")
    assert response.status_code == 200
    assert response.data["count"] == 7  # 6 children + 1 parent

    response = client.get(f"/api/v1.0/items/search/?workspace={other_top_parent.id}")
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
    other_top_parent = factories.ItemFactory(
        title="Item 2", users=[user], type=models.ItemTypeChoices.FOLDER
    )
    for title in titles:
        parent = random.choice(parents)
        children = factories.ItemFactory(
            title=title, parent=parent, type=models.ItemTypeChoices.FILE
        )
        factories.ItemFactory(
            title=title,
            parent=other_top_parent,
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
        f"/api/v1.0/items/search/?type=file&workspace={other_top_parent.id}&title=Project"
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


def test_api_items_search_excludes_children_of_deleted_folders():
    """
    Children of deleted folders should not appear in search results.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    parent = factories.ItemFactory(
        title="folder A",
        parent=top_parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="folder B",
        parent=top_parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="folder A child",
        parent=parent,
        type=models.ItemTypeChoices.FILE,
    )

    parent.soft_delete()

    response = client.get("/api/v1.0/items/search/?title=folder")
    assert response.status_code == 200
    assert response.data["count"] == 1

    titles = [item["title"] for item in response.data["results"]]
    assert "folder B" in titles
    assert "folder A" not in titles
    assert "folder A child" not in titles


def test_api_items_search_deleted_folder_and_children_in_recycle_bin():
    """
    Children of deleted folders should appear when searching in the recycle bin.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    top_parent = factories.ItemFactory(
        title="Item 1",
        creator=user,
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    parent = factories.ItemFactory(
        title="folder A",
        parent=top_parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="folder B",
        parent=top_parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(
        title="folder A child",
        parent=parent,
        type=models.ItemTypeChoices.FILE,
    )

    parent.soft_delete()

    response = client.get("/api/v1.0/items/search/?scope=deleted")
    assert response.status_code == 200
    assert response.data["count"] == 2

    titles = [item["title"] for item in response.data["results"]]
    assert "folder A" in titles
    assert "folder A child" in titles
