"""Tests for restricted folder model behavior."""

from django.core.exceptions import ValidationError

import pytest

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
    """A root folder cannot be restricted: no parent can hold its restriction."""
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
        users=[(user, models.RoleChoices.OWNER)],
    )
    factories.RestrictionFactory(target=folder)

    abilities = folder.get_abilities(user)

    assert abilities["restrict"] is True


def test_models_items_restricted_get_abilities_move_forbidden_on_restricted_root():
    """A restricted folder cannot be moved, even by an explicit owner."""
    user = factories.UserFactory()
    folder = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER,
        users=[(user, models.RoleChoices.OWNER)],
    )

    assert folder.get_abilities(user)["move"] is True

    factories.RestrictionFactory(target=folder)

    assert folder.get_abilities(user)["move"] is False


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
    """A folder is restricted when a restriction targets it."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    assert folder.is_restricted is False
    factories.RestrictionFactory(target=folder)
    assert folder.is_restricted is True
