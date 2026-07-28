"""Tests for shortcut items."""

from django.core.exceptions import ValidationError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_items_shortcuts_factory():
    """The shortcut factory should build a shortcut pointing to a restricted root."""
    shortcut = factories.ShortcutFactory()

    assert shortcut.type == models.ItemTypeChoices.SHORTCUT
    assert shortcut.target.is_restricted is True
    assert shortcut.target.shortcut == shortcut


def test_models_items_shortcuts_require_a_target():
    """A shortcut cannot be created without a target."""
    with pytest.raises(ValidationError):
        factories.ItemFactory(type=models.ItemTypeChoices.SHORTCUT)


@pytest.mark.parametrize("item_type", [models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.FILE])
def test_models_items_shortcuts_target_forbidden_on_other_types(item_type):
    """Only shortcuts can carry a target."""
    target = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, is_restricted=True)

    with pytest.raises(ValidationError):
        factories.ItemFactory(type=item_type, target=target)


def test_models_items_shortcuts_unique_per_target():
    """A restricted folder cannot be targeted by two shortcuts."""
    shortcut = factories.ShortcutFactory()

    with pytest.raises(ValidationError):
        factories.ShortcutFactory(target=shortcut.target)


def test_models_items_shortcuts_deleted_with_their_target():
    """Deleting the target row cascades to its shortcut."""
    shortcut = factories.ShortcutFactory()
    target = shortcut.target

    models.Item.objects.filter(pk=target.pk).delete()

    assert not models.Item.objects.filter(pk=shortcut.pk).exists()


def test_models_items_shortcuts_move_rejects_own_target_subtree():
    """A shortcut cannot be moved under the subtree of its own target."""
    shortcut = factories.ShortcutFactory()
    folder = factories.ItemFactory(
        parent=shortcut.target,
        type=models.ItemTypeChoices.FOLDER,
    )

    with pytest.raises(ValidationError, match="cannot be moved under its own target"):
        shortcut.move(folder)


def test_models_items_shortcuts_detach_deletes_the_row():
    """Detaching a shortcut deletes its row and leaves the target untouched."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    shortcut = folder.shortcut

    shortcut.detach()

    assert not models.Item.objects.filter(pk=shortcut.pk).exists()
    folder.refresh_from_db()
    assert folder.is_restricted is True
    assert str(folder.path) == str(folder.id)
    assert models.ItemAccess.objects.filter(item=folder, user=user, role="owner").exists()


def test_models_items_shortcuts_detach_rejects_other_types():
    """Only shortcuts can be detached."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    with pytest.raises(ValidationError, match="Only shortcuts can be detached"):
        folder.detach()


def test_models_items_shortcuts_item_factory_never_generates_shortcuts():
    """The generic item factory should only draw folder and file types."""
    types = {factories.ItemFactory().type for _ in range(20)}

    assert types <= {models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.FILE}
