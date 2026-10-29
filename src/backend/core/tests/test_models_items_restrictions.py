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


def test_models_items_restrictions_ancestor_soft_delete_trashes_owned_targets():
    """Trashing an ancestor trashes along the restricted folders the user owns."""
    user = factories.UserFactory()
    grandparent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(
        parent=grandparent, type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")]
    )
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction

    grandparent.soft_delete(user)

    restriction.refresh_from_db()
    assert restriction.deleted_at is None
    assert restriction.ancestors_deleted_at == grandparent.deleted_at
    folder.refresh_from_db()
    assert folder.is_restricted is True
    assert folder.deleted_at == grandparent.deleted_at
    assert folder.ancestors_deleted_at == grandparent.deleted_at


def test_models_items_restrictions_ancestor_soft_delete_lifts_unowned_restrictions():
    """Trashing an ancestor lifts the restrictions whose target the user does not own."""
    user = factories.UserFactory()
    grandparent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(
        parent=grandparent, type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")]
    )
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction

    grandparent.soft_delete(factories.UserFactory())

    assert not models.Item.objects.filter(pk=restriction.pk).exists()
    folder.refresh_from_db()
    assert folder.is_restricted is False
    assert folder.deleted_at is None
    assert folder.ancestors_deleted_at is None


def test_models_items_restrictions_ancestor_restore_brings_owned_targets_back():
    """Restoring a trashed ancestor restores the restricted folders trashed along."""
    user = factories.UserFactory()
    grandparent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(
        parent=grandparent, type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")]
    )
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction
    grandparent.soft_delete(user)

    grandparent.restore()

    restriction.refresh_from_db()
    assert restriction.deleted_at is None
    assert restriction.ancestors_deleted_at is None
    folder.refresh_from_db()
    assert folder.is_restricted is True
    assert folder.deleted_at is None
    assert folder.ancestors_deleted_at is None
    assert str(folder.path) == str(folder.id)


def test_models_items_restrictions_ancestor_hard_delete_marks_owned_targets():
    """Hard deleting a trashed ancestor hard deletes the restricted folders trashed along."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    parent.soft_delete(user)

    parent.hard_delete()

    folder.refresh_from_db()
    assert folder.hard_deleted_at is not None


def test_models_items_restrictions_target_soft_delete_trashes_its_restriction():
    """Trashing a restricted folder trashes its restriction along."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction

    folder.soft_delete()

    folder.refresh_from_db()
    restriction.refresh_from_db()
    assert restriction.deleted_at == folder.deleted_at
    assert restriction.ancestors_deleted_at == folder.deleted_at
    assert folder.deleted_at is not None
    assert folder.is_restricted is True
    assert str(folder.path) == str(folder.id)


def test_models_items_restrictions_target_restore_restores_its_restriction():
    """Restoring a restricted folder restores its restriction."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction
    folder.soft_delete()

    folder.restore()

    folder.refresh_from_db()
    restriction.refresh_from_db()
    assert folder.deleted_at is None
    assert folder.is_restricted is True
    assert str(folder.path) == str(folder.id)
    assert restriction.deleted_at is None
    assert restriction.ancestors_deleted_at is None


def test_models_items_restrictions_target_restore_out_of_trashed_subtree_lifts_restriction():
    """Restored while its restriction's subtree is trashed, the folder becomes a plain root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction
    folder.soft_delete()
    parent.soft_delete()

    folder.restore()

    folder.refresh_from_db()
    assert folder.deleted_at is None
    assert str(folder.path) == str(folder.id)
    assert folder.is_restricted is False
    assert not models.Item.objects.filter(pk=restriction.pk).exists()


def test_models_items_restrictions_target_restore_alone_lifts_restriction():
    """Restored alone after being trashed along its tree, the folder becomes a plain root."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction
    parent.soft_delete(user)
    folder.refresh_from_db()

    folder.restore()

    folder.refresh_from_db()
    assert folder.deleted_at is None
    assert folder.is_restricted is False
    assert not models.Item.objects.filter(pk=restriction.pk).exists()


def test_models_items_restrictions_target_hard_delete_marks_the_restriction():
    """Hard deleting a restricted folder hard deletes its restriction."""
    user = factories.UserFactory()
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, users=[(user, "owner")])
    folder = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    folder = folder.restrict(user)
    restriction = folder.restriction
    folder.soft_delete()

    folder.hard_delete()

    restriction.refresh_from_db()
    assert restriction.hard_deleted_at is not None


def test_models_items_restrictions_item_factory_never_generates_restrictions():
    """The generic item factory should only draw folder and file types."""
    types = {factories.ItemFactory().type for _ in range(20)}

    assert types <= {models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.FILE}
