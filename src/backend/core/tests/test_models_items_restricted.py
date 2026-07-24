"""Tests for restricted folder model behavior."""

from django.core.exceptions import ValidationError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_items_restricted_folder_can_be_restricted():
    """A folder is restricted when a restriction targets it."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    assert folder.is_restricted is False
    factories.RestrictionFactory(target=folder)
    assert folder.is_restricted is True
