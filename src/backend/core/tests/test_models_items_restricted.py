"""Tests for restricted folder model behavior."""

from django.core.exceptions import ValidationError

import pytest
from lasuite.drf.models.choices import LinkReachChoices

from core import factories, models

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "role,expected",
    [
        ("owner", True),
        ("administrator", False),
        ("editor", False),
        ("reader", False),
    ],
)
def test_models_items_restricted_get_abilities_restrict_requires_owner(role, expected):
    """Only an owner can restrict a folder."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=folder, user=user, role=role)

    abilities = folder.get_abilities(user)

    assert abilities["restrict"] is expected


def test_models_items_restricted_get_abilities_restrict_forbidden_on_roots():
    """A root folder cannot be restricted: no parent can hold its shortcut."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )

    abilities = folder.get_abilities(user)

    assert abilities["restrict"] is False


def test_models_items_restricted_get_abilities_restrict_allowed_on_restricted_root():
    """An explicit owner can deactivate a restricted folder moved to the root."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        is_restricted=True,
        users=[(user, models.RoleChoices.OWNER)],
    )

    abilities = folder.get_abilities(user)

    assert abilities["restrict"] is True


def test_models_items_restricted_get_abilities_restrict_forbidden_on_files():
    """A file cannot be restricted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    abilities = item.get_abilities(user)

    assert abilities["restrict"] is False


def test_models_items_restricted_get_abilities_restrict_forbidden_when_deleted():
    """A soft deleted folder cannot be restricted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=folder, user=user, role="owner")
    folder.soft_delete()

    abilities = folder.get_abilities(user)

    assert abilities["restrict"] is False


def test_models_items_restricted_folder_can_be_restricted():
    """A folder can be restricted."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, is_restricted=True)
    folder.refresh_from_db()
    assert folder.is_restricted is True


def test_models_items_restricted_file_cannot_be_restricted():
    """A file cannot be restricted."""
    with pytest.raises(ValidationError):
        factories.ItemFactory(type=models.ItemTypeChoices.FILE, is_restricted=True)


def test_models_items_restricted_restrict_moves_folder_to_root():
    """Activating restriction moves the folder and its subtree to the tree root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=folder, type=models.ItemTypeChoices.FILE)

    folder.restrict(user)

    folder.refresh_from_db()
    child.refresh_from_db()
    assert str(folder.path) == str(folder.id)
    assert str(child.path) == f"{folder.id!s}.{child.id!s}"


def test_models_items_restricted_restrict_creates_shortcut():
    """Activating restriction materializes the origin location with a shortcut."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    folder.restrict(user)

    folder.refresh_from_db()
    shortcut = folder.shortcut
    assert shortcut.type == models.ItemTypeChoices.SHORTCUT
    assert str(shortcut.path) == f"{parent.id!s}.{shortcut.id!s}"
    assert shortcut.title == folder.title
    assert shortcut.creator == user


def test_models_items_restricted_restrict_sets_flag_and_creates_owner_access():
    """Activating restriction sets is_restricted and creates an explicit owner access."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    assert not models.ItemAccess.objects.filter(item=folder, user=user).exists()

    folder = folder.restrict(user)

    assert folder.is_restricted is True
    assert models.ItemAccess.objects.filter(item=folder, user=user, role="owner").exists()


def test_models_items_restricted_restrict_keeps_existing_explicit_access():
    """Activating restriction does not duplicate an existing explicit owner access."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=folder, user=user, role="owner")

    folder.restrict(user)

    assert models.ItemAccess.objects.filter(item=folder, user=user, role="owner").count() == 1


def test_models_items_restricted_restrict_promotes_existing_lower_access():
    """Activating restriction promotes an existing lower explicit access to owner."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    access = factories.UserItemAccessFactory(item=folder, user=user, role="reader")

    folder.restrict(user)

    access.refresh_from_db()
    assert access.role == models.RoleChoices.OWNER


def test_models_items_restricted_restrict_defaults_link_reach():
    """Activating restriction sets link reach to restricted when none is explicit."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=LinkReachChoices.PUBLIC,
        link_role="reader",
    )
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=None,
    )

    folder = folder.restrict(user)

    assert folder.link_reach == LinkReachChoices.RESTRICTED


def test_models_items_restricted_restrict_keeps_explicit_link_reach():
    """Activating restriction keeps an existing explicit link reach."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=LinkReachChoices.AUTHENTICATED,
    )

    folder = folder.restrict(user)

    assert folder.link_reach == LinkReachChoices.AUTHENTICATED


def test_models_items_restricted_restrict_requires_a_folder():
    """Only folders can be restricted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)

    with pytest.raises(ValidationError, match="Only folders can be restricted"):
        item.restrict(user)


def test_models_items_restricted_restrict_rejects_already_restricted():
    """A restricted folder cannot be restricted again."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder.restrict(user)
    folder.refresh_from_db()

    with pytest.raises(ValidationError, match="This folder is already restricted"):
        folder.restrict(user)


def test_models_items_restricted_restrict_rejects_roots():
    """A root folder cannot be restricted."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    with pytest.raises(ValidationError, match="A root folder cannot be restricted"):
        folder.restrict(user)


def test_models_items_restricted_restrict_rejects_deleted():
    """A deleted folder cannot be restricted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    parent.soft_delete()
    folder.refresh_from_db()

    with pytest.raises(ValidationError, match="A deleted folder cannot be restricted"):
        folder.restrict(user)


def test_models_items_restricted_cuts_role_inheritance():
    """Roles inherited from former ancestors stop applying once restricted."""
    parent_user = factories.UserFactory()
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_user, models.RoleChoices.OWNER)],
    )
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    folder = folder.restrict(user)

    assert folder.get_role(parent_user) is None
    assert folder.get_role(user) == models.RoleChoices.OWNER


def test_models_items_restricted_descendants_inherit_from_restricted_folder():
    """Descendants inherit the explicit accesses of the restricted folder only."""
    parent_user = factories.UserFactory()
    user = factories.UserFactory()
    reader = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(parent_user, models.RoleChoices.OWNER)],
    )
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=folder, type=models.ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=folder, user=reader, role="reader")

    folder.restrict(user)

    child.refresh_from_db()
    assert child.get_role(reader) == models.RoleChoices.READER
    assert child.get_role(parent_user) is None


def test_models_items_restricted_cuts_link_inheritance():
    """The link definition of former ancestors stops applying once restricted."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        link_reach=LinkReachChoices.PUBLIC,
        link_role="editor",
    )
    folder = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
        link_reach=None,
    )
    child = factories.ItemFactory(parent=folder, type=models.ItemTypeChoices.FILE)

    folder = folder.restrict(user)

    child.refresh_from_db()
    assert folder.computed_link_definition == {
        "link_reach": LinkReachChoices.RESTRICTED,
        "link_role": None,
    }
    assert child.computed_link_definition == {
        "link_reach": LinkReachChoices.RESTRICTED,
        "link_role": None,
    }


def test_models_items_restricted_move_rejects_restricted_roots():
    """A restricted folder cannot be moved: it must be deactivated first."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    other = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)

    with pytest.raises(ValidationError, match="A restricted folder cannot be moved"):
        folder.move(other)
