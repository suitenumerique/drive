"""
Unit tests for the item model, when it is the root of the tree.
"""

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_sub_item_abilities_downgraded():
    """
    Check that the abilities on a sub item created by a user, are downgraded if its role
    is downgraded on the root item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted",
        link_role="reader",
        users=[(user, "editor")],
        type=models.ItemTypeChoices.FOLDER,
        title="root",
    )

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/children/",
        data={
            "type": models.ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
    )

    assert response.status_code == 201

    child = models.Item.objects.get(id=response.json()["id"])

    assert child.get_abilities(user) == {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": True,
        "hard_delete": True,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": True,
        "partial_update": True,
        "restore": False,
        "retrieve": True,
        "tree": True,
        "update": True,
        "upload_ended": True,
    }

    # Downgrade the role on the root item
    access = models.ItemAccess.objects.get(item=item, user=user)
    access.role = "reader"
    access.save()

    assert child.get_abilities(user) == {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": False,
        "children_list": True,
        "destroy": False,
        "hard_delete": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": False,
        "restore": False,
        "retrieve": True,
        "tree": True,
        "update": False,
        "upload_ended": False,
    }


def test_models_items_root_get_abilities_owner(django_assert_num_queries):
    """Check abilities returned for the owner of a item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    expected_abilities = {
        "accesses_manage": True,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": True,
        "hard_delete": True,
        "favorite": True,
        "invite_owner": True,
        "link_configuration": True,
        "media_auth": True,
        "move": False,
        "partial_update": True,
        "restore": True,
        "retrieve": True,
        "tree": True,
        "update": True,
        "upload_ended": True,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    expected_abilities["move"] = False
    assert item.get_abilities(user) == expected_abilities


def test_models_items_root_get_abilities_administrator(django_assert_num_queries):
    """Check abilities returned for the administrator of a item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "administrator")])
    expected_abilities = {
        "accesses_manage": True,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": False,
        "hard_delete": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": True,
        "media_auth": True,
        "move": False,
        "partial_update": True,
        "restore": False,
        "retrieve": True,
        "tree": True,
        "update": True,
        "upload_ended": True,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


def test_models_items_root_get_abilities_editor_user(django_assert_num_queries):
    """Check abilities returned for the editor of a root item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "editor")])
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": True,
        "children_list": True,
        "destroy": False,
        "hard_delete": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": False,
        "restore": False,
        "retrieve": True,
        "tree": True,
        "update": False,
        "upload_ended": True,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())


def test_models_items_root_get_abilities_reader_user(django_assert_num_queries):
    """Check abilities returned for the reader of a root item."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "reader")])
    access_from_link = item.link_reach != "restricted" and item.link_role == "editor"
    expected_abilities = {
        "accesses_manage": False,
        "accesses_view": True,
        "children_create": access_from_link,
        "children_list": True,
        "destroy": False,
        "hard_delete": False,
        "favorite": True,
        "invite_owner": False,
        "link_configuration": False,
        "media_auth": True,
        "move": False,
        "partial_update": False,
        "restore": False,
        "retrieve": True,
        "tree": True,
        "update": False,
        "upload_ended": access_from_link,
    }
    with django_assert_num_queries(1):
        assert item.get_abilities(user) == expected_abilities
    item.soft_delete()
    item.refresh_from_db()
    assert all(value is False for value in item.get_abilities(user).values())
