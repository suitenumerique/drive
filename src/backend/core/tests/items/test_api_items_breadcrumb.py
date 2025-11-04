"""Test API items breadcrumb."""

import uuid

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_items_api_breadcrumb_non_existing_item():
    """Test the breadcrumb API endpoint with a non-existing item."""
    item_id = uuid.uuid4()
    response = APIClient().get(f"/api/v1.0/items/{item_id}/breadcrumb/")

    assert response.status_code == 404


def test_items_api_breadcrumb_anonymous_to_a_non_public_tree_structure():
    """Anonymous user can not access a non-public tree structure."""
    # root
    root = factories.ItemFactory(
        title="root",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        main_workspace=True,
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

    response = APIClient().get(f"/api/v1.0/items/{level2_1.id}/breadcrumb/")

    assert response.status_code == 401


def test_items_api_anonymous_to_a_public_breadcrumb_structure():
    """Anonymous user can access a public breadcrumb structure."""
    user = factories.UserFactory()
    # root, should not be visible in the returned tree
    root = factories.ItemFactory(
        title="root",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        creator=user,
        main_workspace=True,
    )

    # Other root, with link_reach set to public. This one should not be visible in the returned tree
    factories.ItemFactory(
        title="root_alone",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
        creator=user,
        main_workspace=True,
    )

    # child of level1 are not link_reach set to public
    level1_1 = factories.ItemFactory(
        parent=root,
        title="level1_1",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
        creator=user,
    )
    level1_2 = factories.ItemFactory(
        parent=root,
        title="level1_2",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
        creator=user,
    )

    # Populare level1_1 with authenticated link_reach
    factories.ItemFactory.create_batch(
        3,
        parent=level1_1,
        type=models.ItemTypeChoices.FILE,
        creator=user,
    )

    # level 2 have one item with link_reach set to public and an other set to authenticated
    level2_1 = factories.ItemFactory(
        title="level2_1",
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        creator=user,
    )
    # No matter the linnk_reach of this item, it must be visible in the returned tree
    factories.ItemFactory(
        title="level2_2",
        parent=level1_2,
        type=models.ItemTypeChoices.FOLDER,
        creator=user,
    )

    response = APIClient().get(f"/api/v1.0/items/{level2_1.id}/breadcrumb/")

    assert response.status_code == 200

    assert response.json() == [
        {
            "id": str(level1_2.id),
            "title": "level1_2",
            "path": str(level1_2.path),
            "depth": 2,
            "main_workspace": False,
        },
        {
            "id": str(level2_1.id),
            "title": "level2_1",
            "path": str(level2_1.path),
            "depth": 3,
            "main_workspace": False,
        },
    ]


def test_items_api_breadcrumb_authenticated_direct_access(django_assert_num_queries):
    """Test the breadcrumb API endpoint with items owned by the current user."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.UserItemAccessFactory(
        user=user,
        item__title="root",
        item__type=models.ItemTypeChoices.FOLDER,
        item__main_workspace=True,
    )
    # another root alone, not visible in the returned tree
    factories.UserItemAccessFactory(
        user=user,
        item__title="root_alone",
        item__type=models.ItemTypeChoices.FOLDER,
        item__main_workspace=True,
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
    factories.UserItemAccessFactory(
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

    with django_assert_num_queries(5):
        # access to the tree for level2_2
        response = client.get(f"/api/v1.0/items/{level3_1.item.id}/breadcrumb/")

    assert response.status_code == 200

    assert response.json() == [
        {
            "id": str(root.item.id),
            "title": "root",
            "path": str(root.item.path),
            "depth": 1,
            "main_workspace": True,
        },
        {
            "id": str(level1_1.item.id),
            "title": "level1_1",
            "path": str(level1_1.item.path),
            "depth": 2,
            "main_workspace": False,
        },
        {
            "id": str(level2_2.item.id),
            "title": "level2_2",
            "path": str(level2_2.item.path),
            "depth": 3,
            "main_workspace": False,
        },
        {
            "id": str(level3_1.item.id),
            "title": "level3_1",
            "path": str(level3_1.item.path),
            "depth": 4,
            "main_workspace": False,
        },
    ]


def test_api_items_breadcrumb_authenticated_with_access_authenticated():
    """Test the breadcrumb API endpoint with items link_reach set to RESTRICTED."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Root is restricted and is not visible in the returned tree
    root = factories.ItemFactory(
        title="root",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.RESTRICTED,
        main_workspace=True,
    )

    # Other root, with link_reach set to public. This one should not be visible in the returned tree
    factories.ItemFactory(
        title="root_alone",
        type=models.ItemTypeChoices.FOLDER,
        link_reach=models.LinkReachChoices.PUBLIC,
        main_workspace=True,
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
    factories.ItemFactory(
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

    response = client.get(f"/api/v1.0/items/{level2_2.id}/breadcrumb/")
    assert response.status_code == 200

    assert response.json() == [
        {
            "id": str(level1_1.id),
            "title": "level1_1",
            "path": str(level1_1.path),
            "depth": 2,
            "main_workspace": False,
        },
        {
            "id": str(level2_2.id),
            "title": "level2_2",
            "path": str(level2_2.path),
            "depth": 3,
            "main_workspace": False,
        },
    ]
