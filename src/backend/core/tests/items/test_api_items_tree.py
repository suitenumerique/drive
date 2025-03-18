"""Tests for tree API endpoint"""
# pylint: disable=too-many-lines

import uuid

from django.contrib.auth.models import AnonymousUser

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_items_api_tree_non_existing_item():
    """Test the tree API endpoint with a non-existing item."""
    item_id = uuid.uuid4()
    response = APIClient().get(f"/api/v1.0/items/{item_id}/tree/")

    assert response.status_code == 404


def test_items_api_tree_anonymous_to_a_non_public_tree_structure():
    """Anonymous user can not access a non-public tree structure."""
    # root
    root = factories.ItemFactory(
        title="root",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # Other root, with link_reach set to public. This one should not be visible in the returned tree
    factories.ItemFactory(
        title="root_alone",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    # child of level1 are not like_react set to public
    level1_1, level1_2 = factories.ItemFactory.create_batch(
        2,
        parent=root,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # Populare level1_1 with authenticated link_reach
    factories.ItemFactory.create_batch(
        3,
        parent=level1_1,
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # level 2 have one item with link_reach set to public and an other set to authenticated
    level2_1 = factories.ItemFactory(
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )
    factories.ItemFactory(
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    response = APIClient().get(f"/api/v1.0/items/{level2_1.id}/tree/")

    assert response.status_code == 401


def test_items_api_anonymous_to_a_public_tree_structure():
    """Anonymous user can access a public tree structure."""
    # root, should not be visible in the returned tree
    root = factories.ItemFactory(
        title="root",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # Other root, with link_reach set to public. This one should not be visible in the returned tree
    factories.ItemFactory(
        title="root_alone",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    # child of level1 are not link_reach set to public
    level1_1 = factories.ItemFactory(
        parent=root,
        title="level1_1",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )
    level1_2 = factories.ItemFactory(
        parent=root,
        title="level1_2",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    # Populare level1_1 with authenticated link_reach
    factories.ItemFactory.create_batch(
        3,
        parent=level1_1,
        type=models.ItemTypeChoices.FILE,
    )

    # level 2 have one item with link_reach set to public and an other set to authenticated
    level2_1 = factories.ItemFactory(
        title="level2_1",
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    # No matter the linnk_reach of this item, it must be visible in the returned tree
    level2_2 = factories.ItemFactory(
        title="level2_2",
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
    )

    response = APIClient().get(f"/api/v1.0/items/{level2_1.id}/tree/")

    assert response.status_code == 200
    assert response.json() == {
        "abilities": level1_2.get_abilities(AnonymousUser()),
        "children": [
            {
                "abilities": level2_1.get_abilities(AnonymousUser()),
                "children": [],
                "created_at": level2_1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": str(level2_1.creator.id),
                "depth": 3,
                "id": str(level2_1.id),
                "is_favorite": False,
                "link_reach": level2_1.link_reach,
                "link_role": level2_1.link_role,
                "nb_accesses": 0,
                "numchild": 0,
                "numchild_folder": 0,
                "path": "0000000.0000001.0000000",
                "title": "level2_1",
                "type": level2_1.type,
                "updated_at": level2_1.updated_at.isoformat().replace("+00:00", "Z"),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": [],
            },
            {
                "abilities": level2_2.get_abilities(AnonymousUser()),
                "children": [],
                "created_at": level2_2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": str(level2_2.creator.id),
                "depth": 3,
                "id": str(level2_2.id),
                "is_favorite": False,
                "link_reach": level2_2.link_reach,
                "link_role": level2_2.link_role,
                "nb_accesses": 0,
                "numchild": 0,
                "numchild_folder": 0,
                "path": "0000000.0000001.0000001",
                "title": "level2_2",
                "type": level2_2.type,
                "updated_at": level2_2.updated_at.isoformat().replace("+00:00", "Z"),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": [],
            },
        ],
        "created_at": level1_2.created_at.isoformat().replace("+00:00", "Z"),
        "creator": str(level1_2.creator.id),
        "depth": 2,
        "id": str(level1_2.id),
        "is_favorite": False,
        "link_reach": level1_2.link_reach,
        "link_role": level1_2.link_role,
        "nb_accesses": 0,
        "numchild": 2,
        "numchild_folder": 2,
        "path": "0000000.0000001",
        "title": "level1_2",
        "type": level1_2.type,
        "updated_at": level1_2.updated_at.isoformat().replace("+00:00", "Z"),
        "upload_state": None,
        "url": None,
        "mimetype": None,
        "user_roles": [],
    }


def test_items_api_tree_authenticated_direct_access(django_assert_num_queries):
    """Test the tree API endpoint with items owned by the current user."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.UserItemAccessFactory(
        user=user, item__title="root", item__type=models.ItemTypeChoices.FOLDER
    )
    # another root alone, not visible in the returned tree
    factories.UserItemAccessFactory(
        user=user, item__title="root_alone", item__type=models.ItemTypeChoices.FOLDER
    )

    level1_1 = factories.UserItemAccessFactory(
        user=user,
        item__title="level1_1",
        item__parent=root.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    level1_2 = factories.UserItemAccessFactory(
        user=user,
        item__title="level1_2",
        item__parent=root.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    level1_3 = factories.UserItemAccessFactory(
        user=user,
        item__title="level1_3",
        item__parent=root.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )

    # attach files to root
    factories.UserItemAccessFactory.create_batch(
        2, user=user, item__parent=root.item, item__type=models.ItemTypeChoices.FILE
    )
    # attach files to level1_1
    factories.UserItemAccessFactory.create_batch(
        3, user=user, item__parent=level1_1.item, item__type=models.ItemTypeChoices.FILE
    )
    # Attach folders to level2_1, visible in the returned tree
    level2_1 = factories.UserItemAccessFactory(
        user=user,
        item__title="level2_1",
        item__parent=level1_1.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    level2_2 = factories.UserItemAccessFactory(
        user=user,
        item__title="level2_2",
        item__parent=level1_1.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    # attach folders to level1_2, not visible in the returned tree
    factories.UserItemAccessFactory(
        user=user,
        item__title="level2_3",
        item__parent=level1_2.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        user=user,
        item__title="level2_4",
        item__parent=level1_2.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    # attach folders to level1_3, not visible in the returned tree
    factories.UserItemAccessFactory(
        user=user,
        item__title="level2_5",
        item__parent=level1_3.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )

    # attach files to level2_2, not visible in the returned tree
    factories.UserItemAccessFactory.create_batch(
        4, user=user, item__parent=level2_2.item, item__type=models.ItemTypeChoices.FILE
    )
    # Add a folder inside level2_2, not visible in the returned tree
    level3_1 = factories.UserItemAccessFactory(
        user=user,
        item__title="level3_1",
        item__parent=level2_2.item,
        item__type=models.ItemTypeChoices.FOLDER,
    )

    # Without nb_accesses cache
    with django_assert_num_queries(12):
        # access to the tree for level2_2
        client.get(f"/api/v1.0/items/{level3_1.item.id}/tree/")

    # With nb_accesses cache
    with django_assert_num_queries(5):
        # access to the tree for level2_2
        response = client.get(f"/api/v1.0/items/{level3_1.item.id}/tree/")

    assert response.status_code == 200
    assert response.json() == {
        "abilities": root.item.get_abilities(user),
        "children": [
            {
                "abilities": level1_1.item.get_abilities(user),
                "children": [
                    {
                        "abilities": level2_1.item.get_abilities(user),
                        "children": [],
                        "created_at": level2_1.item.created_at.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "creator": str(level2_1.item.creator.id),
                        "depth": 3,
                        "id": str(level2_1.item.id),
                        "is_favorite": False,
                        "link_reach": level2_1.item.link_reach,
                        "link_role": level2_1.item.link_role,
                        "nb_accesses": 3,
                        "numchild": 0,
                        "numchild_folder": 0,
                        "path": "0000000.0000000.0000003",
                        "title": "level2_1",
                        "type": level2_1.item.type,
                        "updated_at": level2_1.item.updated_at.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "upload_state": None,
                        "url": None,
                        "mimetype": None,
                        "user_roles": list(level2_1.item.get_roles(user)),
                    },
                    {
                        "abilities": level2_2.item.get_abilities(user),
                        "children": [
                            {
                                "abilities": level3_1.item.get_abilities(user),
                                "children": [],
                                "created_at": level3_1.item.created_at.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "creator": str(level3_1.item.creator.id),
                                "depth": 4,
                                "id": str(level3_1.item.id),
                                "is_favorite": False,
                                "link_reach": level3_1.item.link_reach,
                                "link_role": level3_1.item.link_role,
                                "nb_accesses": 4,
                                "numchild": 0,
                                "numchild_folder": 0,
                                "path": "0000000.0000000.0000004.0000004",
                                "title": "level3_1",
                                "type": level3_1.item.type,
                                "updated_at": level3_1.item.updated_at.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "upload_state": None,
                                "url": None,
                                "mimetype": None,
                                "user_roles": list(level3_1.item.get_roles(user)),
                            },
                        ],
                        "created_at": level2_2.item.created_at.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "creator": str(level2_2.item.creator.id),
                        "depth": 3,
                        "id": str(level2_2.item.id),
                        "is_favorite": False,
                        "link_reach": level2_2.item.link_reach,
                        "link_role": level2_2.item.link_role,
                        "nb_accesses": 3,
                        "numchild": 5,
                        "numchild_folder": 1,
                        "path": "0000000.0000000.0000004",
                        "title": "level2_2",
                        "type": level2_2.item.type,
                        "updated_at": level2_2.item.updated_at.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "upload_state": None,
                        "url": None,
                        "mimetype": None,
                        "user_roles": list(level2_2.item.get_roles(user)),
                    },
                ],
                "created_at": level1_1.item.created_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "creator": str(level1_1.item.creator.id),
                "depth": 2,
                "id": str(level1_1.item.id),
                "is_favorite": False,
                "link_reach": level1_1.item.link_reach,
                "link_role": level1_1.item.link_role,
                "nb_accesses": 2,
                "numchild": 5,
                "numchild_folder": 2,
                "path": "0000000.0000000",
                "title": "level1_1",
                "type": level1_1.item.type,
                "updated_at": level1_1.item.updated_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": list(level1_1.item.get_roles(user)),
            },
            {
                "abilities": level1_2.item.get_abilities(user),
                "children": [],
                "created_at": level1_2.item.created_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "creator": str(level1_2.item.creator.id),
                "depth": 2,
                "id": str(level1_2.item.id),
                "is_favorite": False,
                "link_reach": level1_2.item.link_reach,
                "link_role": level1_2.item.link_role,
                "nb_accesses": 2,
                "numchild": 2,
                "numchild_folder": 2,
                "path": "0000000.0000001",
                "title": "level1_2",
                "type": level1_2.item.type,
                "updated_at": level1_2.item.updated_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": list(level1_2.item.get_roles(user)),
            },
            {
                "abilities": level1_3.item.get_abilities(user),
                "children": [],
                "created_at": level1_3.item.created_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "creator": str(level1_3.item.creator.id),
                "depth": 2,
                "id": str(level1_3.item.id),
                "is_favorite": False,
                "link_reach": level1_3.item.link_reach,
                "link_role": level1_3.item.link_role,
                "nb_accesses": 2,
                "numchild": 1,
                "numchild_folder": 1,
                "path": "0000000.0000002",
                "title": "level1_3",
                "type": level1_3.item.type,
                "updated_at": level1_3.item.updated_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": list(level1_3.item.get_roles(user)),
            },
        ],
        "created_at": root.item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": str(root.item.creator.id),
        "depth": 1,
        "id": str(root.item.id),
        "is_favorite": False,
        "link_reach": root.item.link_reach,
        "link_role": root.item.link_role,
        "nb_accesses": 1,
        "numchild": 5,
        "numchild_folder": 3,
        "path": "0000000",
        "title": "root",
        "type": root.item.type,
        "updated_at": root.item.updated_at.isoformat().replace("+00:00", "Z"),
        "upload_state": None,
        "url": None,
        "mimetype": None,
        "user_roles": list(root.item.get_roles(user)),
    }


def test_api_items_tree_authenticated_with_access_authenticated():
    """Test the tree API endpoint with items link_reach set to RESTRICTED."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Root is restricted and is not visible in the returned tree
    root = factories.ItemFactory(
        title="root",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
    )

    # Other root, with link_reach set to public. This one should not be visible in the returned tree
    factories.ItemFactory(
        title="root_alone",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
    )

    # first level are set to AUTHENTICATED, only level1_1 should be visible in the returned tree
    # because it will an ancestor of the targeted item
    level1_1 = factories.ItemFactory(
        title="level1_1",
        parent=root,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )
    level1_2 = factories.ItemFactory(
        title="level1_2",
        parent=root,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )
    level1_3 = factories.ItemFactory(
        title="level1_3",
        parent=root,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # Attach folders to level1_2 and level1_3, not visible in the returned tree
    factories.ItemFactory.create_batch(
        2,
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )
    factories.ItemFactory.create_batch(
        2,
        parent=level1_3,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # Add an other level to level1_1, visible in the returned tree
    level2_1 = factories.ItemFactory(
        title="level2_1",
        parent=level1_1,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )
    level2_2 = factories.ItemFactory(
        title="level2_2",
        parent=level1_1,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    # Add files to level2_2, not visible in the returned tree
    factories.ItemFactory.create_batch(
        4,
        parent=level2_2,
        type=models.ItemTypeChoices.FILE,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
    )

    response = client.get(f"/api/v1.0/items/{level2_2.id}/tree/")
    assert response.status_code == 200
    assert response.json() == {
        "created_at": level1_1.created_at.isoformat().replace("+00:00", "Z"),
        "creator": str(level1_1.creator.id),
        "depth": 2,
        "id": str(level1_1.id),
        "is_favorite": False,
        "link_reach": "authenticated",
        "link_role": level1_1.link_role,
        "nb_accesses": 0,
        "numchild": 2,
        "numchild_folder": 2,
        "path": "0000000.0000000",
        "title": "level1_1",
        "type": "folder",
        "updated_at": level1_1.updated_at.isoformat().replace("+00:00", "Z"),
        "upload_state": None,
        "url": None,
        "mimetype": None,
        "user_roles": [],
        "abilities": level1_1.get_abilities(user),
        "children": [
            {
                "abilities": level2_1.get_abilities(user),
                "children": [],
                "created_at": level2_1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": str(level2_1.creator.id),
                "depth": 3,
                "id": str(level2_1.id),
                "is_favorite": False,
                "link_reach": "authenticated",
                "link_role": level2_1.link_role,
                "nb_accesses": 0,
                "numchild": 0,
                "numchild_folder": 0,
                "path": "0000000.0000000.0000000",
                "title": "level2_1",
                "type": "folder",
                "updated_at": level2_1.updated_at.isoformat().replace("+00:00", "Z"),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": [],
            },
            {
                "abilities": level2_2.get_abilities(user),
                "children": [],
                "created_at": level2_2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": str(level2_2.creator.id),
                "depth": 3,
                "id": str(level2_2.id),
                "is_favorite": False,
                "link_reach": "authenticated",
                "link_role": level2_2.link_role,
                "nb_accesses": 0,
                "numchild": 4,
                "numchild_folder": 0,
                "path": "0000000.0000000.0000001",
                "title": "level2_2",
                "type": "folder",
                "updated_at": level2_2.updated_at.isoformat().replace("+00:00", "Z"),
                "upload_state": None,
                "url": None,
                "mimetype": None,
                "user_roles": [],
            },
        ],
    }
