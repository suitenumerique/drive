"""Tests for restricted folder model behavior."""

from django.core.exceptions import ValidationError

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_items_restricted_folder_can_be_restricted():
    """A folder can be restricted."""
    folder = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, is_restricted=True)
    folder.refresh_from_db()
    assert folder.is_restricted is True


def test_models_items_restricted_file_cannot_be_restricted():
    """A file cannot be restricted."""
    with pytest.raises(ValidationError):
        factories.ItemFactory(type=models.ItemTypeChoices.FILE, is_restricted=True)
