"""
Unit tests for the lookups relying on item paths being made of item ids
"""

from django.db.models import F, Value

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


@pytest.fixture(name="tree")
def fixture_tree():
    """
    Build two trees:
        root > parent > child
             > sibling > nephew
        other_root
    """
    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    sibling = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    nephew = factories.ItemFactory(parent=sibling, type=models.ItemTypeChoices.FOLDER)
    other_root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    return {
        "root": root,
        "parent": parent,
        "child": child,
        "sibling": sibling,
        "nephew": nephew,
        "other_root": other_root,
    }


def test_models_items_id_in_path(tree):
    """IdInPath should match the item at a path and its ancestors only."""
    accesses = {name: factories.UserItemAccessFactory(item=item) for name, item in tree.items()}

    matched = models.ItemAccess.objects.filter(
        models.IdInPath(F("item_id"), Value(str(tree["child"].path)))
    )

    assert set(matched) == {accesses["root"], accesses["parent"], accesses["child"]}
