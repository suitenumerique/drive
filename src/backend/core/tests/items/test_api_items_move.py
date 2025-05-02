"""
Test moving items within the item tree via an detail action API endpoint.
"""

import random
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

# pytest.skip("move API is not re implemented using ltree yet", allow_module_level=True)


def test_api_items_move_anonymous_user():
    """Anonymous users should not be able to move items."""
    item = factories.ItemFactory()
    target = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    assert response.status_code == 401
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
    }


@pytest.mark.parametrize("role", [None, "reader", "editor"])
def test_api_items_move_authenticated_item_no_permission(role):
    """
    Authenticated users should not be able to move items with insufficient
    permissions on the origin item.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    target = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=models.ItemTypeChoices.FOLDER
    ).item

    if role:
        factories.UserItemAccessFactory(item=item, user=user, role=role)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }


def test_api_items_move_invalid_target_string():
    """Test for moving an item to an invalid target as a random string."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=models.ItemTypeChoices.FOLDER
    ).item
    item_child = factories.ItemFactory(users=[(user, "owner")], parent=item)

    response = client.post(
        f"/api/v1.0/items/{item_child.id!s}/move/",
        data={"target_item_id": "non-existent-id"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "target_item_id",
                "code": "invalid",
                "detail": "Must be a valid UUID.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_move_invalid_target_uuid():
    """Test for moving an item to an invalid target that looks like a UUID."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.UserItemAccessFactory(
        user=user, role="owner", item__type=models.ItemTypeChoices.FOLDER
    ).item
    item_child = factories.ItemFactory(users=[(user, "owner")], parent=item)

    response = client.post(
        f"/api/v1.0/items/{item_child.id!s}/move/",
        data={"target_item_id": str(uuid4())},
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "target_item_id",
                "code": "item_move_target_does_not_exist",
                "detail": "Target parent item does not exist.",
            },
        ],
        "type": "validation_error",
    }


@pytest.mark.parametrize("target_parent_role", models.RoleChoices.values)
@pytest.mark.parametrize("target_role", models.RoleChoices.values)
def test_api_tems_move_file_authenticated_target_roles_mocked(
    target_role, target_parent_role
):
    """
    Authenticated users with insufficient permissions on the target item (or its
    parent depending on the position chosen), should not be allowed to move items.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    power_roles = ["administrator", "owner", "editor"]

    item_parent = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    item = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FILE,
        parent=item_parent,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    target_parent = factories.ItemFactory(
        users=[(user, target_parent_role)],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    _sibling1, target, _sibling2 = factories.ItemFactory.create_batch(
        3,
        parent=target_parent,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    models.ItemAccess.objects.create(item=target, user=user, role=target_role)
    target_children = factories.ItemFactory.create_batch(2, parent=target)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    item.refresh_from_db()
    if target_role in power_roles or target_parent_role in power_roles:
        assert response.status_code == 200
        assert response.json() == {"message": "item moved successfully."}

        assert list(target.children()) == [item] + target_children
    else:
        assert response.status_code == 400
        message = (
            "You do not have permission to move items as a child to this target item."
        )
        assert response.json() == {
            "errors": [
                {
                    "attr": "target_item_id",
                    "code": "item_move_missing_permission",
                    "detail": message,
                },
            ],
            "type": "validation_error",
        }


@pytest.mark.parametrize("target_parent_role", models.RoleChoices.values)
@pytest.mark.parametrize("target_role", models.RoleChoices.values)
def test_api_items_move_authenticated_target_roles_mocked(
    target_role, target_parent_role
):
    """
    Authenticated users with insufficient permissions on the target item (or its
    parent depending on the position chosen), should not be allowed to move items.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    power_roles = ["administrator", "owner", "editor"]

    item_parent = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    item = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FOLDER,
        parent=item_parent,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    # children
    factories.ItemFactory.create_batch(
        3, parent=item, type=models.ItemTypeChoices.FOLDER
    )

    target_parent = factories.ItemFactory(
        users=[(user, target_parent_role)],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    _sibling1, target, _sibling2 = factories.ItemFactory.create_batch(
        3,
        parent=target_parent,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    models.ItemAccess.objects.create(item=target, user=user, role=target_role)
    target_children = factories.ItemFactory.create_batch(2, parent=target)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    item.refresh_from_db()
    if target_role in power_roles or target_parent_role in power_roles:
        assert response.status_code == 200
        assert response.json() == {"message": "item moved successfully."}

        assert list(target.children()) == [item] + target_children
        assert (
            list(target.descendants())
            == [item] + list(item.descendants()) + target_children
        )

    else:
        assert response.status_code == 400
        message = (
            "You do not have permission to move items as a child to this target item."
        )
        assert response.json() == {
            "errors": [
                {
                    "attr": "target_item_id",
                    "code": "item_move_missing_permission",
                    "detail": message,
                },
            ],
            "type": "validation_error",
        }


def test_api_items_move_authenticated_deleted_item():
    """
    It should not be possible to move a deleted item or its descendants, even
    for an owner.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        users=[(user, "owner")],
        type=models.ItemTypeChoices.FOLDER,
    )
    child = factories.ItemFactory(parent=item, users=[(user, "owner")])
    item.soft_delete()

    target = factories.ItemFactory(users=[(user, "owner")])

    # Try moving the deleted item
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )
    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }

    # Verify that the item has not moved
    item.refresh_from_db()
    assert item.parent() is None

    # Try moving the child of the deleted item
    response = client.post(
        f"/api/v1.0/items/{child.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )
    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }

    # Verify that the child has not moved
    child.refresh_from_db()
    assert child.parent() == item


def test_api_items_move_authenticated_target_not_folder_should_fail():
    """Moving an item to a target that is not a folder is not allowed."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER
    )
    item_child = factories.ItemFactory(users=[(user, "owner")], parent=item)
    target = factories.ItemFactory(
        users=[(user, "owner")], type=models.ItemTypeChoices.FILE
    )

    # trying to move the item to a not folder target
    response = client.post(
        f"/api/v1.0/items/{item_child.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "target",
                "code": "item_move_target_not_a_folder",
                "detail": "Only folders can be targeted when moving an item",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_move_authenticated_deleted_target_as_child():
    """
    It should not be possible to move an item as a child of a deleted target
    even for a owner.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER
    )
    item_child = factories.ItemFactory(users=[(user, "owner")], parent=item)

    target = factories.ItemFactory(
        users=[(user, "owner")],
        type=models.ItemTypeChoices.FOLDER,
    )
    child = factories.ItemFactory(
        parent=target, users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER
    )
    target.soft_delete()

    # Try moving the item to the deleted target
    response = client.post(
        f"/api/v1.0/items/{item_child.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "target_item_id",
                "code": "item_move_target_does_not_exist",
                "detail": "Target parent item does not exist.",
            },
        ],
        "type": "validation_error",
    }

    # Verify that the item has not moved
    item.refresh_from_db()
    assert item.parent() is None

    # Try moving the item to the child of the deleted target
    response = client.post(
        f"/api/v1.0/items/{item_child.id!s}/move/",
        data={"target_item_id": str(child.id)},
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "target_item_id",
                "code": "item_move_target_does_not_exist",
                "detail": "Target parent item does not exist.",
            },
        ],
        "type": "validation_error",
    }

    # Verify that the item has not moved
    item.refresh_from_db()
    assert item.parent() is None


def test_api_items_move_authenticated_deleted_target_as_sibling():
    """
    It should not be possible to move an item as a sibling of a deleted target item
    if the user has no rigths on its parent.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER
    )
    item_child = factories.ItemFactory(users=[(user, "owner")], parent=item)

    target_parent = factories.ItemFactory(
        users=[(user, "owner")],
        type=models.ItemTypeChoices.FOLDER,
    )
    target = factories.ItemFactory(users=[(user, "owner")], parent=target_parent)
    target_parent.soft_delete()

    # Try moving the item as a sibling of the target
    response = client.post(
        f"/api/v1.0/items/{item_child.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "target_item_id",
                "code": "item_move_target_does_not_exist",
                "detail": "Target parent item does not exist.",
            },
        ],
        "type": "validation_error",
    }

    # Verify that the item has not moved
    item.refresh_from_db()
    assert item.parent() is None


def test_api_items_move_with_descendants():
    """
    Moving an item with descendants should move the descendants as well.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item_parent = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    item = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        parent=item_parent,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    item_child_folder = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        parent=item,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    item_child_file = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FILE,
        parent=item,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    item_sub_child_file = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FILE,
        parent=item_child_folder,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    target = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )

    assert len(target.children()) == 0
    assert len(target.descendants()) == 0

    assert len(item_parent.children()) == 1

    assert len(item.children()) == 2
    assert len(item.descendants()) == 3

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    item_parent.refresh_from_db()
    item.refresh_from_db()
    item_child_folder.refresh_from_db()
    item_child_file.refresh_from_db()
    item_sub_child_file.refresh_from_db()
    target.refresh_from_db()
    assert response.status_code == 200
    assert response.json() == {"message": "item moved successfully."}

    assert len(target.children()) == 1
    assert len(target.descendants()) == 4

    assert len(item_parent.children()) == 0

    assert len(item.children()) == 2
    assert len(item.descendants()) == 3
