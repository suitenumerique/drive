"""
Test moving items within the item tree via an detail action API endpoint.
"""

import random
from unittest import mock
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
def test_api_tems_move_file_authenticated_target_roles_mocked(target_role, target_parent_role):
    """
    Authenticated users with insufficient permissions on the target item (or its
    parent depending on the position chosen), should not be allowed to move items.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    power_roles = ["administrator", "owner"]
    children_create_roles = power_roles + ["editor"]

    item_parent = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=item_parent,
    )

    target_parent = factories.ItemFactory(
        users=[(user, target_parent_role)],
        type=models.ItemTypeChoices.FOLDER,
    )
    _sibling1, target, _sibling2 = factories.ItemFactory.create_batch(
        3,
        parent=target_parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    models.ItemAccess.objects.create(item=target, user=user, role=target_role)
    target_children = factories.ItemFactory.create_batch(2, parent=target)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    item.refresh_from_db()
    target.refresh_from_db()
    target_parent.refresh_from_db()
    if (
        target_role in children_create_roles
        or target_parent_role in children_create_roles
        or target.computed_link_role in children_create_roles
        or target_parent.computed_link_role in children_create_roles
    ):
        assert response.status_code == 200
        assert response.json() == {"message": "item moved successfully."}

        assert list(target.children()) == [item] + target_children
    else:
        assert response.status_code == 400
        message = "You do not have permission to move items as a child to this target item."
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
def test_api_items_move_authenticated_target_roles_mocked(target_role, target_parent_role):
    """
    Authenticated users with insufficient permissions on the target item (or its
    parent depending on the position chosen), should not be allowed to move items.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    power_roles = ["administrator", "owner"]
    children_create_roles = power_roles + ["editor"]

    item_parent = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        users=[(user, random.choice(power_roles))],
        type=models.ItemTypeChoices.FOLDER,
        parent=item_parent,
    )

    # children
    factories.ItemFactory.create_batch(3, parent=item, type=models.ItemTypeChoices.FOLDER)

    target_parent = factories.ItemFactory(
        users=[(user, target_parent_role)],
        type=models.ItemTypeChoices.FOLDER,
    )
    _sibling1, target, _sibling2 = factories.ItemFactory.create_batch(
        3,
        parent=target_parent,
        type=models.ItemTypeChoices.FOLDER,
    )

    models.ItemAccess.objects.create(item=target, user=user, role=target_role)
    target_children = factories.ItemFactory.create_batch(2, parent=target)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )

    item.refresh_from_db()
    target.refresh_from_db()
    target_parent.refresh_from_db()
    if (
        target_role in children_create_roles
        or target_parent_role in children_create_roles
        or target.computed_link_role in children_create_roles
        or target_parent.computed_link_role in children_create_roles
    ):
        assert response.status_code == 200
        assert response.json() == {"message": "item moved successfully."}

        assert list(target.children()) == [item] + target_children
        assert list(target.descendants()) == [item] + list(item.descendants()) + target_children

    else:
        assert response.status_code == 400
        message = "You do not have permission to move items as a child to this target item."
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

    item = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
    item_child = factories.ItemFactory(users=[(user, "owner")], parent=item)
    target = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FILE)

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

    item = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
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

    item = factories.ItemFactory(users=[(user, "owner")], type=models.ItemTypeChoices.FOLDER)
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


def test_api_items_move_suspicious_item_should_not_work_for_non_creator():
    """
    Non-creators should not be able to move suspicious items.
    """
    creator = factories.UserFactory()
    other_user = factories.UserFactory()
    client = APIClient()
    client.force_login(other_user)

    suspicious_item = factories.ItemFactory(
        creator=creator,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[
            (creator, models.RoleChoices.OWNER),
            (other_user, models.RoleChoices.ADMIN),
        ],
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
    )

    target = factories.ItemFactory(
        users=[(other_user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    response = client.post(
        f"/api/v1.0/items/{suspicious_item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )
    assert response.status_code == 404


def test_api_items_move_suspicious_item_should_work_for_creator():
    """
    Creators should be able to move their own suspicious items.
    """
    creator = factories.UserFactory()
    client = APIClient()
    client.force_login(creator)

    folder = factories.ItemFactory(
        creator=creator,
        users=[(creator, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    suspicious_item = factories.ItemFactory(
        creator=creator,
        parent=folder,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[(creator, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
    )

    target = factories.ItemFactory(
        users=[(creator, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    response = client.post(
        f"/api/v1.0/items/{suspicious_item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "item moved successfully."}

    # Verify that the item has moved
    suspicious_item.refresh_from_db()
    assert suspicious_item.parent() == target


def test_api_items_move_to_root():
    """
    Creators should be able to move their own items to the root.
    The user that moves the item become the creator of the item.
    """
    creator = factories.UserFactory()
    mover = factories.UserFactory()
    client = APIClient()
    client.force_login(mover)

    folder = factories.ItemFactory(
        creator=creator,
        users=[(creator, models.RoleChoices.OWNER), (mover, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        title="folder",
    )

    item = factories.ItemFactory(
        creator=creator,
        parent=folder,
        type=models.ItemTypeChoices.FOLDER,
        title="folder child",
    )

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "item moved successfully."}

    # Verify that the item has moved
    item.refresh_from_db()
    assert item.parent() is None

    # Verify that the item is available in the root
    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["results"][0]["id"] == str(item.id)
    assert response.json()["results"][1]["id"] == str(folder.id)

    item.refresh_from_db()
    assert item.creator == mover


def test_api_items_move_to_root_force_link_reach():
    """
    When moving an item to the root and no link_reach is set, force it to be restricted.
    """
    creator = factories.UserFactory()
    mover = factories.UserFactory()
    client = APIClient()
    client.force_login(mover)

    folder = factories.ItemFactory(
        creator=creator,
        users=[(creator, models.RoleChoices.OWNER), (mover, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        title="folder",
    )

    item = factories.ItemFactory(
        creator=creator,
        parent=folder,
        type=models.ItemTypeChoices.FOLDER,
        title="folder child",
        link_reach=None,
    )

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "item moved successfully."}

    # Verify that the item has moved
    item.refresh_from_db()
    assert item.parent() is None

    # Verify that the item is available in the root
    response = client.get("/api/v1.0/items/")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["results"][0]["id"] == str(item.id)
    assert response.json()["results"][1]["id"] == str(folder.id)

    item.refresh_from_db()
    assert item.creator == mover
    assert item.link_reach == models.LinkReachChoices.RESTRICTED


def test_api_items_force_syncing_link_reach_with_parents():
    """
    When moving an item in an other item, force it to be sync with its parent's link reach.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        parent=parent,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    target = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    assert item.link_reach == models.LinkReachChoices.AUTHENTICATED
    assert item.computed_link_reach == models.LinkReachChoices.AUTHENTICATED

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/move/",
        data={"target_item_id": str(target.id)},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "item moved successfully."}

    item.refresh_from_db()

    assert item.link_reach is None
    assert item.computed_link_reach == models.LinkReachChoices.AUTHENTICATED


# Posthog events


def test_api_items_move_posthog_event(settings):
    """Moving an item should send an 'item_moved' event."""
    settings.POSTHOG_KEY = "fake-key"
    user = factories.UserFactory()
    item = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    target = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    client = APIClient()
    client.force_login(user)

    with mock.patch("core.api.viewsets.posthog_capture") as mock_capture:
        response = client.post(
            f"/api/v1.0/items/{item.id!s}/move/",
            data={"target_item_id": str(target.id)},
        )

    assert response.status_code == 200
    mock_capture.assert_called_once_with(
        "item_moved",
        user,
        {},
        item=item,
    )


def test_api_items_move_missing_permission_posthog_event(settings):
    """Moving an item without permission on target should send a
    'item_move_missing_permission' event."""
    settings.POSTHOG_KEY = "fake-key"
    user = factories.UserFactory()
    item = factories.ItemFactory(
        users=[(user, models.RoleChoices.OWNER)],
        type=models.ItemTypeChoices.FOLDER,
    )
    target = factories.ItemFactory(
        users=[(user, models.RoleChoices.READER)],
        type=models.ItemTypeChoices.FOLDER,
    )

    client = APIClient()
    client.force_login(user)

    with mock.patch("core.api.viewsets.posthog_capture") as mock_capture:
        response = client.post(
            f"/api/v1.0/items/{item.id!s}/move/",
            data={"target_item_id": str(target.id)},
        )

    assert response.status_code == 400
    mock_capture.assert_called_once_with(
        "item_move_missing_permission",
        user,
        {},
        item=item,
    )


# -----------------------------------------------------------------------------
# Encryption-aware move tests
#
# The crypto itself runs client-side; the backend only routes payload fields
# into the right DB columns and validates that the requested transition is
# coherent with the item's current state. These tests stub plausible
# base64-ish opaque blobs and assert state transitions, not crypto.
# -----------------------------------------------------------------------------


def _encrypted_root(user, role="owner"):
    """Build a self-rooted encrypted folder owned by `user`.

    Mirrors what the /encrypt/ endpoint produces: `is_encrypted=True`,
    `encrypted_symmetric_key=NULL`, with the user's wrap stored on the
    ItemAccess row.
    """
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.UserItemAccessFactory(
        item=item,
        user=user,
        role=role,
        encrypted_item_symmetric_key_for_user="WRAP-USER-ROOT",
        encryption_public_key_fingerprint="fp-root",
    )
    return item


def _encrypted_child(parent, *, item_type=models.ItemTypeChoices.FOLDER):
    """Build a chained-encrypted descendant of `parent`."""
    return factories.ItemFactory(
        type=item_type,
        parent=parent,
        is_encrypted=True,
        encrypted_symmetric_key=f"CHAIN-WRAP-{uuid4().hex[:8]}",
    )


def test_api_items_move_encrypted_same_tree_rewrap():
    """
    Case 2: moving an encrypted descendant from one folder to another
    inside the SAME encryption tree just rewrites its chain wrap.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    folder_a = _encrypted_child(root)
    folder_b = _encrypted_child(root)
    file_item = _encrypted_child(folder_a, item_type=models.ItemTypeChoices.FILE)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(folder_b.id),
            "encrypted_symmetric_key": "NEW-CHAIN-WRAP-UNDER-B",
        },
        format="json",
    )

    assert response.status_code == 200
    file_item.refresh_from_db()
    assert file_item.is_encrypted is True
    assert file_item.encrypted_symmetric_key == "NEW-CHAIN-WRAP-UNDER-B"
    # No per-user wrap should land on the moved item's access rows.
    assert not models.ItemAccess.objects.filter(
        item=file_item,
        encrypted_item_symmetric_key_for_user__isnull=False,
    ).exists()


def test_api_items_move_encrypted_same_tree_missing_wrap_rejected():
    """Same-tree rewrap must come with the new chain wrap."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    folder_a = _encrypted_child(root)
    folder_b = _encrypted_child(root)
    file_item = _encrypted_child(folder_a, item_type=models.ItemTypeChoices.FILE)
    original_wrap = file_item.encrypted_symmetric_key

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={"target_item_id": str(folder_b.id)},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_encrypted_key_required"
    file_item.refresh_from_db()
    # Item must NOT have moved on a rejected payload — atomicity matters
    # since a half-applied move would leave the chain wrap stale.
    assert file_item.encrypted_symmetric_key == original_wrap


def test_api_items_move_re_anchor_to_plaintext():
    """
    Case 3: chained source → plaintext destination. The item flips to
    its own encryption root, the chain wrap is cleared, and per-user
    wraps land on access rows on this item.
    """
    user = factories.UserFactory()
    other = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    # `other` has access to the encrypted tree via an inherited row
    # on the root — they don't have an ItemAccess on the file itself.
    factories.UserItemAccessFactory(
        item=root,
        user=other,
        role="reader",
        encrypted_item_symmetric_key_for_user="WRAP-OTHER-ROOT",
        encryption_public_key_fingerprint="fp-other",
    )
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)

    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(plain_target.id),
            "is_encryption_root": True,
            "per_user_encrypted_keys": {
                user.sub: "WRAP-USER-NEW-ROOT",
                other.sub: "WRAP-OTHER-NEW-ROOT",
            },
            "encryption_public_key_fingerprints": {
                user.sub: "fp-user",
                other.sub: "fp-other",
            },
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    file_item.refresh_from_db()
    assert file_item.is_encrypted is True
    assert file_item.encrypted_symmetric_key is None  # promoted to root
    # The mover already had an ItemAccess on the encryption root, but not
    # on the file itself — re-anchor materialises a row for them on this
    # item with the wrap.
    user_access = models.ItemAccess.objects.get(item=file_item, user=user)
    assert user_access.encrypted_item_symmetric_key_for_user == "WRAP-USER-NEW-ROOT"
    assert user_access.encryption_public_key_fingerprint == "fp-user"
    other_access = models.ItemAccess.objects.get(item=file_item, user=other)
    assert other_access.encrypted_item_symmetric_key_for_user == "WRAP-OTHER-NEW-ROOT"


def test_api_items_move_re_anchor_with_pending_collaborator():
    """
    Re-anchor must accept `null` per-user wraps for collaborators
    without a published pubkey — they land as pending access rows
    (mirrors /encrypt/'s "pending invite" semantics).
    """
    user = factories.UserFactory()
    pending = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    factories.UserItemAccessFactory(
        item=root, user=pending, role="reader",
        encrypted_item_symmetric_key_for_user=None,  # pending on root too
        encryption_public_key_fingerprint=None,
    )
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)

    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")],
    )

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(plain_target.id),
            "is_encryption_root": True,
            "per_user_encrypted_keys": {
                user.sub: "WRAP-USER-NEW-ROOT",
                pending.sub: None,
            },
            "encryption_public_key_fingerprints": {
                user.sub: "fp-user",
                pending.sub: None,
            },
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    pending_access = models.ItemAccess.objects.get(item=file_item, user=pending)
    assert pending_access.encrypted_item_symmetric_key_for_user is None
    assert pending_access.encryption_public_key_fingerprint is None


def test_api_items_move_re_anchor_caller_must_have_wrap():
    """
    Re-anchor must refuse if the caller (mover) has a `null` wrap for
    themselves — they'd lock themselves out of their own file. The
    refusal is the ONE actor-only guard; other collaborators are
    allowed null.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)
    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")],
    )

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(plain_target.id),
            "is_encryption_root": True,
            "per_user_encrypted_keys": {user.sub: None},
            "encryption_public_key_fingerprints": {user.sub: None},
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_caller_wrap_required"


def test_api_items_move_re_anchor_into_encrypted_rejected():
    """Cannot promote to encryption root inside another encrypted tree."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root_a = _encrypted_root(user)
    file_item = _encrypted_child(root_a, item_type=models.ItemTypeChoices.FILE)
    root_b = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(root_b.id),
            "is_encryption_root": True,
            "per_user_encrypted_keys": {user.sub: "WRAP"},
            "encryption_public_key_fingerprints": {user.sub: "fp"},
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_promote_into_encrypted"


def test_api_items_move_demote_self_rooted_into_chain():
    """
    Case 4: a self-rooted encrypted item moving INTO an encrypted
    subtree picks up a chain wrap and clears its per-user wraps.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Self-rooted file the user holds via per-user wrap.
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.UserItemAccessFactory(
        item=file_item,
        user=user,
        role="owner",
        encrypted_item_symmetric_key_for_user="WRAP-USER-FILE-ROOT",
        encryption_public_key_fingerprint="fp-user",
    )

    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "is_encryption_root": False,
            "encrypted_symmetric_key": "CHAIN-WRAP-UNDER-DEST",
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    file_item.refresh_from_db()
    assert file_item.is_encrypted is True
    assert file_item.encrypted_symmetric_key == "CHAIN-WRAP-UNDER-DEST"
    # Per-user wrap KEPT alongside the chain wrap. The destination
    # chain may not cover the same set of users that held explicit
    # access on this self-rooted file; clearing the wrap would
    # silently revoke collaborators outside the chain. Hybrid is fine
    # — chain users use the chain, originals use their per-user wrap.
    user_access = models.ItemAccess.objects.get(item=file_item, user=user)
    assert user_access.encrypted_item_symmetric_key_for_user == "WRAP-USER-FILE-ROOT"
    assert user_access.encryption_public_key_fingerprint == "fp-user"


def test_api_items_move_demote_preserves_outsider_wrap():
    """
    Demoting must NOT revoke collaborators who had explicit per-user
    access on the self-rooted item but are not part of the destination
    chain. Their wrap is the only path they have to decrypt — clearing
    it would silently lock them out despite their ItemAccess.role
    staying intact.
    """
    user = factories.UserFactory()
    outsider = factories.UserFactory()  # has access to the file, NOT to dest tree
    client = APIClient()
    client.force_login(user)

    # Self-rooted file shared with `user` and `outsider`.
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.UserItemAccessFactory(
        item=file_item, user=user, role="owner",
        encrypted_item_symmetric_key_for_user="WRAP-USER-FILE",
        encryption_public_key_fingerprint="fp-user",
    )
    factories.UserItemAccessFactory(
        item=file_item, user=outsider, role="reader",
        encrypted_item_symmetric_key_for_user="WRAP-OUTSIDER-FILE",
        encryption_public_key_fingerprint="fp-outsider",
    )

    # Destination tree only `user` has access to.
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "is_encryption_root": False,
            "encrypted_symmetric_key": "CHAIN-WRAP-UNDER-DEST",
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    # Outsider's per-user wrap survives the demote — their decryption
    # path now bypasses the chain (which they can't reach) and uses
    # their wrap on this item directly.
    outsider_access = models.ItemAccess.objects.get(item=file_item, user=outsider)
    assert outsider_access.encrypted_item_symmetric_key_for_user == "WRAP-OUTSIDER-FILE"
    assert outsider_access.encryption_public_key_fingerprint == "fp-outsider"


def test_api_items_move_demote_requires_chain_wrap():
    """Demote must come with `encrypted_symmetric_key`."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.UserItemAccessFactory(
        item=file_item, user=user, role="owner",
        encrypted_item_symmetric_key_for_user="WRAP", encryption_public_key_fingerprint="fp",
    )
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "is_encryption_root": False,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_chain_wrap_required"


def test_api_items_move_demote_to_plaintext_rejected():
    """Demote requires the destination to be encrypted."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        is_encrypted=True,
        encrypted_symmetric_key=None,
    )
    factories.UserItemAccessFactory(
        item=file_item, user=user, role="owner",
        encrypted_item_symmetric_key_for_user="WRAP", encryption_public_key_fingerprint="fp",
    )
    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")],
    )

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(plain_target.id),
            "is_encryption_root": False,
            "encrypted_symmetric_key": "WRAP",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_demote_to_plain"


def test_api_items_move_plaintext_into_encrypted_rejected():
    """
    Plaintext → encrypted is refused at the move endpoint — the client
    must encrypt the source first via /encrypt/, then retry the move.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, "owner")],
    )
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "encrypted_symmetric_key": "WRAP",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_plaintext_into_encrypted"


def test_api_items_move_encrypt_on_move_file():
    """
    Plaintext file → encrypted folder via encrypt-on-move: file becomes
    chain-wrapped under the destination, NO ItemAccess rows materialised
    for inherited-only collaborators (the whole point of the new shape).
    """
    user = factories.UserFactory()
    other = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Source is a plaintext folder both `user` and `other` have access
    # to. Putting `other` here would normally cause /encrypt/ to
    # materialise a per-user wrap row for them — encrypt-on-move must
    # not.
    source_folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner"), (other, "reader")],
    )
    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        parent=source_folder,
    )
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "encrypted_symmetric_key": "CHAIN-WRAP-FILE-UNDER-DEST",
            "encrypted_keys_for_descendants": {},
            "file_key_mapping": {},
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    file_item.refresh_from_db()
    assert file_item.is_encrypted is True
    assert file_item.encrypted_symmetric_key == "CHAIN-WRAP-FILE-UNDER-DEST"
    # No per-user ItemAccess wrap created for the inherited `other`
    # collaborator. They had inherited access via the source folder;
    # they no longer have any access to the file (it moved out of
    # source's subtree). That's exactly the cleanup we wanted.
    assert (
        models.ItemAccess.objects.filter(
            item=file_item,
            encrypted_item_symmetric_key_for_user__isnull=False,
        ).count()
        == 0
    )


def test_api_items_move_encrypt_on_move_folder_with_descendants():
    """Folder with nested files: every effective descendant gets its
    chain wrap; the root carries the chain wrap under the destination.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    src_folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, "owner")],
    )
    nested_folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, parent=src_folder,
    )
    file_a = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, parent=src_folder,
    )
    file_b = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, parent=nested_folder,
    )
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{src_folder.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "encrypted_symmetric_key": "CHAIN-WRAP-SRC-UNDER-DEST",
            "encrypted_keys_for_descendants": {
                str(nested_folder.id): "wrap-nested-under-src",
                str(file_a.id): "wrap-file-a-under-src",
                str(file_b.id): "wrap-file-b-under-nested",
            },
            "file_key_mapping": {
                str(file_a.id): "encrypted_a.bin",
                str(file_b.id): "encrypted_b.bin",
            },
        },
        format="json",
    )

    assert response.status_code == 200, response.json()
    src_folder.refresh_from_db()
    nested_folder.refresh_from_db()
    file_a.refresh_from_db()
    file_b.refresh_from_db()
    assert src_folder.is_encrypted is True
    assert src_folder.encrypted_symmetric_key == "CHAIN-WRAP-SRC-UNDER-DEST"
    assert nested_folder.is_encrypted is True
    assert nested_folder.encrypted_symmetric_key == "wrap-nested-under-src"
    assert file_a.is_encrypted is True
    assert file_a.encrypted_symmetric_key == "wrap-file-a-under-src"
    assert file_a.filename == "encrypted_a.bin"
    assert file_b.encrypted_symmetric_key == "wrap-file-b-under-nested"
    assert file_b.filename == "encrypted_b.bin"


def test_api_items_move_encrypt_on_move_subtree_mutation_rejected():
    """If a descendant appears between frontend discovery and the
    commit, the mismatched id set must abort with 409 — same contract
    as /encrypt/.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    src_folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")],
    )
    file_a = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, parent=src_folder,
    )
    # Live extra: the client didn't see this one when it built the
    # payload.
    factories.ItemFactory(type=models.ItemTypeChoices.FILE, parent=src_folder)
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{src_folder.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "encrypted_symmetric_key": "wrap",
            "encrypted_keys_for_descendants": {str(file_a.id): "wrap-a"},
            "file_key_mapping": {},
        },
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "subtree_mutated"


def test_api_items_move_encrypt_on_move_requires_chain_wrap():
    """`encrypted_symmetric_key` is mandatory for encrypt-on-move."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, "owner")],
    )
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "encrypted_keys_for_descendants": {},
            "file_key_mapping": {},
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_chain_wrap_required"


def test_api_items_move_encrypt_on_move_rejects_encrypted_source():
    """Encrypt-on-move payload with an already-encrypted source is a
    contract violation — the rewrap/demote shapes apply instead.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)
    dest_root = _encrypted_root(user)

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(dest_root.id),
            "encrypted_symmetric_key": "wrap",
            "encrypted_keys_for_descendants": {},
            "file_key_mapping": {},
        },
        format="json",
    )

    assert response.status_code == 400
    assert (
        response.json()["errors"][0]["code"]
        == "item_move_encrypt_on_move_source_encrypted"
    )


def test_api_items_move_encrypt_on_move_rejects_plain_target():
    """Encrypt-on-move with a plaintext destination is meaningless —
    if the destination isn't encrypted there's no chain to attach to.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file_item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE, users=[(user, "owner")],
    )
    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")],
    )

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={
            "target_item_id": str(plain_target.id),
            "encrypted_symmetric_key": "wrap",
            "encrypted_keys_for_descendants": {},
            "file_key_mapping": {},
        },
        format="json",
    )

    assert response.status_code == 400
    assert (
        response.json()["errors"][0]["code"]
        == "item_move_encrypt_on_move_plain_target"
    )


def test_api_items_move_chained_to_plain_without_re_anchor_rejected():
    """
    Chained-encrypted → plaintext WITHOUT the re-anchor flag is refused
    — the bare move would leave the item with a stale chain wrap and
    no resolvable parent chain.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = _encrypted_root(user)
    file_item = _encrypted_child(root, item_type=models.ItemTypeChoices.FILE)
    plain_target = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")],
    )

    response = client.post(
        f"/api/v1.0/items/{file_item.id!s}/move/",
        data={"target_item_id": str(plain_target.id)},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "item_move_re_anchor_required"
