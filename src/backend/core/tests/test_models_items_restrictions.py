"""Tests for restriction items."""

from django.core.exceptions import ValidationError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_items_restrictions_factory():
    """The restriction factory should build a restriction pointing to a restricted root."""
    restriction = factories.RestrictionFactory()

    assert restriction.type == models.ItemTypeChoices.RESTRICTION
    assert restriction.target.is_restricted is True
    assert restriction.target.restriction == restriction


def test_models_items_restrictions_require_a_target():
    """A restriction cannot be created without a target."""
    with pytest.raises(ValidationError):
        factories.ItemFactory(type=models.ItemTypeChoices.RESTRICTION)


@pytest.mark.parametrize("item_type", [models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.FILE])
def test_models_items_restrictions_target_forbidden_on_other_types(item_type):
    """Only restrictions can carry a target."""
    target = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    with pytest.raises(ValidationError):
        factories.ItemFactory(type=item_type, target=target)


def test_models_items_restrictions_unique_per_target():
    """A restricted folder cannot be targeted by two restrictions."""
    restriction = factories.RestrictionFactory()

    with pytest.raises(ValidationError):
        factories.RestrictionFactory(target=restriction.target)


def test_models_items_restrictions_deleted_with_their_target():
    """Deleting the target row cascades to its restriction."""
    restriction = factories.RestrictionFactory()
    target = restriction.target

    models.Item.objects.filter(pk=target.pk).delete()

    assert not models.Item.objects.filter(pk=restriction.pk).exists()


def test_models_items_restrictions_move_rejects_own_target_subtree():
    """A restriction cannot be moved under the subtree of its own target."""
    restriction = factories.RestrictionFactory()
    folder = factories.ItemFactory(
        parent=restriction.target,
        type=models.ItemTypeChoices.FOLDER,
    )

    with pytest.raises(ValidationError, match="cannot be moved under its own target"):
        restriction.move(folder)


def test_models_items_restrictions_detach_deletes_the_row():
    """Detaching a restriction deletes its row, the target becomes a plain root folder."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction

    restriction.detach()

    assert not models.Item.objects.filter(pk=restriction.pk).exists()
    folder.refresh_from_db()
    assert folder.is_restricted is False
    assert str(folder.path) == str(folder.id)
    assert models.ItemAccess.objects.filter(item=folder, user=user, role="owner").exists()


def test_models_items_restrictions_detach_rejects_other_types():
    """Only restrictions can be detached."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    with pytest.raises(ValidationError, match="Only restrictions can be detached"):
        folder.detach()


def test_models_items_restrictions_item_factory_never_generates_restrictions():
    """The generic item factory should only draw folder and file types."""
    types = {factories.ItemFactory().type for _ in range(20)}

    assert types <= {models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.FILE}
