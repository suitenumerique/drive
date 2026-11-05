"""
Tests for the `source` field recording the provenance of items.
"""

import pytest

from core import factories

pytestmark = pytest.mark.django_db


def test_item_factory_default_source_is_none():
    """Items without known provenance (e.g. pre-existing data) keep source null."""
    item = factories.ItemFactory()
    assert item.source is None
