"""
Unit tests for the itemAccess model
"""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

import pytest

from core import factories

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
    """A item can have several item accesses with an empty team."""
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
    """A item can have several item accesses with a null user."""
    access = factories.TeamItemAccessFactory()
    factories.TeamItemAccessFactory(item=access.item)


def test_models_item_accesses_user_and_team_set():
    """User and team can't both be set on a item access."""
    with pytest.raises(
        ValidationError,
        match="Either user or team must be set, not both.",
    ):
        factories.UserItemAccessFactory(team="my-team")


def test_models_item_accesses_user_and_team_empty():
    """User and team can't both be empty on a item access."""
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
    Check abilities of self access for the owner of a item when
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
        "set_role_to": ["administrator", "editor", "reader"],
    }


def test_models_item_access_get_abilities_for_owner_of_self_last():
    """
    Check abilities of self access for the owner of a item when there is only one owner left.
    """
    access = factories.UserItemAccessFactory(role="owner")
    abilities = access.get_abilities(access.user)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_owner_of_owner():
    """Check abilities of owner access for the owner of a item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["administrator", "editor", "reader"],
    }


def test_models_item_access_get_abilities_for_owner_of_administrator():
    """Check abilities of administrator access for the owner of a item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["owner", "editor", "reader"],
    }


def test_models_item_access_get_abilities_for_owner_of_editor():
    """Check abilities of editor access for the owner of a item."""
    access = factories.UserItemAccessFactory(role="editor")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["owner", "administrator", "reader"],
    }


def test_models_item_access_get_abilities_for_owner_of_reader():
    """Check abilities of reader access for the owner of a item."""
    access = factories.UserItemAccessFactory(role="reader")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="owner").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["owner", "administrator", "editor"],
    }


# - for administrator


def test_models_item_access_get_abilities_for_administrator_of_owner():
    """Check abilities of owner access for the administrator of a item."""
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
    """Check abilities of administrator access for the administrator of a item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["editor", "reader"],
    }


def test_models_item_access_get_abilities_for_administrator_of_editor():
    """Check abilities of editor access for the administrator of a item."""
    access = factories.UserItemAccessFactory(role="editor")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["administrator", "reader"],
    }


def test_models_item_access_get_abilities_for_administrator_of_reader():
    """Check abilities of reader access for the administrator of a item."""
    access = factories.UserItemAccessFactory(role="reader")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="administrator").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "update": True,
        "partial_update": True,
        "set_role_to": ["administrator", "editor"],
    }


# - for editor


def test_models_item_access_get_abilities_for_editor_of_owner():
    """Check abilities of owner access for the editor of a item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="editor").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_editor_of_administrator():
    """Check abilities of administrator access for the editor of a item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="editor").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_editor_of_editor_user(
    django_assert_num_queries,
):
    """Check abilities of editor access for the editor of a item."""
    access = factories.UserItemAccessFactory(role="editor")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="editor").user

    with django_assert_num_queries(1):
        abilities = access.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


# - for reader


def test_models_item_access_get_abilities_for_reader_of_owner():
    """Check abilities of owner access for the reader of a item."""
    access = factories.UserItemAccessFactory(role="owner")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_reader_of_administrator():
    """Check abilities of administrator access for the reader of a item."""
    access = factories.UserItemAccessFactory(role="administrator")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_for_reader_of_reader_user(
    django_assert_num_queries,
):
    """Check abilities of reader access for the reader of a item."""
    access = factories.UserItemAccessFactory(role="reader")
    factories.UserItemAccessFactory(item=access.item)  # another one
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user

    with django_assert_num_queries(1):
        abilities = access.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }


def test_models_item_access_get_abilities_preset_role(django_assert_num_queries):
    """No query is done if the role is preset, e.g., with a query annotation."""
    access = factories.UserItemAccessFactory(role="reader")
    user = factories.UserItemAccessFactory(item=access.item, role="reader").user
    access.user_role = "reader"

    with django_assert_num_queries(1):
        abilities = access.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "update": False,
        "partial_update": False,
        "set_role_to": [],
    }
