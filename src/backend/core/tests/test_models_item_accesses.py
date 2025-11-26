"""
Unit tests for the itemAccess model
"""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_item_accesses_str():
    """
    The str representation should include user email, item title and role.
    """
    user = factories.UserFactory(email="david.bowman@example.com")
    access = factories.UserItemAccessFactory(
        role="reader",
        user=user,
        item__title="admins",
    )
    assert str(access) == "david.bowman@example.com is reader in item admins"


def test_models_item_accesses_unique_user():
    """item accesses should be unique for a given couple of user and item."""
    access = factories.UserItemAccessFactory()

    with pytest.raises(
        ValidationError,
        match="This user is already in this item.",
    ):
        factories.UserItemAccessFactory(user=access.user, item=access.item)


def test_models_item_accesses_several_empty_teams():
    """an item can have several item accesses with an empty team."""
    access = factories.UserItemAccessFactory()
    factories.UserItemAccessFactory(item=access.item)


def test_models_item_accesses_unique_team():
    """item accesses should be unique for a given couple of team and item."""
    access = factories.TeamItemAccessFactory()

    with pytest.raises(
        ValidationError,
        match="This team is already in this item.",
    ):
        factories.TeamItemAccessFactory(team=access.team, item=access.item)


def test_models_item_accesses_several_null_users():
    """an item can have several item accesses with a null user."""
    access = factories.TeamItemAccessFactory()
    factories.TeamItemAccessFactory(item=access.item)


def test_models_item_accesses_user_and_team_set():
    """User and team can't both be set on an item access."""
    with pytest.raises(
        ValidationError,
        match="Either user or team must be set, not both.",
    ):
        factories.UserItemAccessFactory(team="my-team")


def test_models_item_accesses_user_and_team_empty():
    """User and team can't both be empty on an item access."""
    with pytest.raises(
        ValidationError,
        match="Either user or team must be set, not both.",
    ):
        factories.UserItemAccessFactory(user=None)


# get_abilities


def test_models_item_access_get_abilities_anonymous():
    """Check abilities returned for an anonymous user."""
    access = factories.UserItemAccessFactory()
    abilities = access.get_abilities(AnonymousUser())
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_authenticated():
    """Check abilities returned for an authenticated user."""
    access = factories.UserItemAccessFactory()
    user = factories.UserFactory()
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


# - for owner


def test_models_item_access_get_abilities_for_owner_of_self_allowed():
    """
    Check abilities of self access for the owner of an item when
    there is more than one owner left.
    """
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item, role="owner")
    abilities = access.get_abilities(access.user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }


def test_models_item_access_get_abilities_for_owner_of_self_last_on_root(
    django_assert_num_queries,
):
    """
    Check abilities of self access for the owner of a root item when there
    is only one owner left.
    """
    access = factories.UserItemAccessFactory(role="owner")

    with django_assert_num_queries(3):
        abilities = access.get_abilities(access.user)

    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_owner_of_self_last_on_child(
    django_assert_num_queries,
):
    """
    Check abilities of self access for the owner of a child item when there
    is only one owner left.
    """
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    access = factories.UserItemAccessFactory(item__parent=parent, role="owner")

    with django_assert_num_queries(2):
        abilities = access.get_abilities(access.user)

    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }


def test_models_item_access_get_abilities_for_owner_of_owner():
    """Check abilities of owner access for the owner of an item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }


def test_models_item_access_get_abilities_for_owner_of_administrator():
    """Check abilities of administrator access for the owner of an item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }


def test_models_item_access_get_abilities_for_owner_of_editor():
    """Check abilities of editor access for the owner of an item."""
    access = factories.UserItemAccessFactory(role="editor")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }


def test_models_item_access_get_abilities_for_owner_of_reader():
    """Check abilities of reader access for the owner of an item."""
    access = factories.UserItemAccessFactory(role="reader")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }


# - for administrator


def test_models_item_access_get_abilities_for_administrator_of_owner():
    """Check abilities of owner access for the administrator of an item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_administrator_of_administrator():
    """Check abilities of administrator access for the administrator of an item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator"],
    }


def test_models_item_access_get_abilities_for_administrator_of_editor():
    """Check abilities of editor access for the administrator of an item."""
    access = factories.UserItemAccessFactory(role="editor")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator"],
    }


def test_models_item_access_get_abilities_for_administrator_of_reader():
    """Check abilities of reader access for the administrator of an item."""
    access = factories.UserItemAccessFactory(role="reader")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["reader", "editor", "administrator"],
    }


# - for editor


def test_models_item_access_get_abilities_for_editor_of_owner():
    """Check abilities of owner access for the editor of an item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="editor").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_editor_of_administrator():
    """Check abilities of administrator access for the editor of an item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="editor").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_editor_of_editor_user(
    django_assert_num_queries,
):
    """Check abilities of editor access for the editor of an item."""
    access = factories.UserItemAccessFactory(role="editor")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="editor").user

    with django_assert_num_queries(2):
        abilities = access.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


# - for reader


def test_models_item_access_get_abilities_for_reader_of_owner():
    """Check abilities of owner access for the reader of an item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_reader_of_administrator():
    """Check abilities of administrator access for the reader of an item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_reader_of_reader_user(
    django_assert_num_queries,
):
    """Check abilities of reader access for the reader of an item."""
    access = factories.UserItemAccessFactory(role="reader")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user

    with django_assert_num_queries(2):
        abilities = access.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


@pytest.mark.parametrize("role", models.RoleChoices)
def test_models_item_access_get_abilities_retrieve_own_access(role):
    """Check abilities of self access for the owner of an item."""
    access = factories.UserItemAccessFactory(role=role)
    abilities = access.get_abilities(access.user)
    assert abilities["retrieve"] is True


def test_models_item_access_get_abilities_explicit():
    """
    test case with a combination of explicit accesses and inherited accesses.
    An explicit access id added on the root item with a "weak" role (editor)
    and then an explicit access is added on the deepest item with a "strong" role (owner).
    The `set_role_to` should take of ancestors roles to determine the available roles.
    """
    user = factories.UserFactory()
    other_owner = factories.UserFactory()

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    # explicit access on root.
    root_access = factories.UserItemAccessFactory(item=root, user=user, role="editor")
    # explicit access on item.
    item_access = factories.UserItemAccessFactory(item=item, user=user, role="owner")

    # Explicit owner access on root for other owner.
    factories.UserItemAccessFactory(item=root, user=other_owner, role="owner")

    factories.UserItemAccessFactory(item=root, role="administrator")
    factories.UserItemAccessFactory(item=root, role="owner")

    assert item.get_role(user) == "owner"

    # User with inherited accesses on its own accesses.

    assert root_access.get_abilities(user) == {
        "destroy": False,
        "update": False,
        "partial_update": False,
        "retrieve": True,
        "set_role_to": [],
    }

    assert item_access.get_abilities(user) == {
        "destroy": True,
        "update": True,
        "partial_update": True,
        "retrieve": True,
        "set_role_to": ["editor", "administrator", "owner"],
    }

    # Owner user on the root item, acting on the previous user's accesses.

    assert root_access.get_abilities(other_owner) == {
        "destroy": True,
        "update": True,
        "partial_update": True,
        "retrieve": True,
        "set_role_to": ["reader", "editor", "administrator", "owner"],
    }

    assert item_access.max_ancestors_role == "editor"
    assert item_access.get_abilities(other_owner) == {
        "destroy": True,
        "update": True,
        "partial_update": True,
        "retrieve": True,
        "set_role_to": ["editor", "administrator", "owner"],
    }
