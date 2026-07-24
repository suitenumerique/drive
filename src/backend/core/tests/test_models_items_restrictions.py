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


def test_models_items_restrictions_item_factory_never_generates_restrictions():
    """The generic item factory should only draw folder and file types."""
    types = {factories.ItemFactory().type for _ in range(20)}

    assert types <= {models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.FILE}
