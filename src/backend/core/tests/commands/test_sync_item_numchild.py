"""
Test suite for management commands.
"""

from io import StringIO

from django.core.management import call_command

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_sync_item_numchild_dry_run():
    """Test the command in dry run mode."""
    # Create a folder with children
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    # Manually corrupt the numchild values
    parent.numchild = 0
    parent.numchild_folder = 0
    parent.save(update_fields=["numchild", "numchild_folder"])

    output = StringIO()
    call_command("sync_item_numchild", "--dry-run", stdout=output)

    # Refresh from database
    parent.refresh_from_db()

    # Values should not have changed in dry run
    assert parent.numchild == 0
    assert parent.numchild_folder == 0

    # Output should indicate what would be updated
    output_str = output.getvalue()
    assert "DRY RUN MODE" in output_str
    assert "would be updated" in output_str


def test_sync_item_numchild_updates_values():
    """Test that the command correctly updates numchild values."""
    # Create a folder with children
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)

    # Manually corrupt the numchild values
    parent.numchild = 0
    parent.numchild_folder = 0
    parent.save(update_fields=["numchild", "numchild_folder"])

    output = StringIO()
    call_command("sync_item_numchild", stdout=output)

    # Refresh from database
    parent.refresh_from_db()

    # Values should be corrected
    assert parent.numchild == 3  # 3 total children
    assert parent.numchild_folder == 1  # 1 folder child

    # Output should indicate successful update
    output_str = output.getvalue()
    assert "Successfully updated" in output_str


def test_sync_item_numchild_ignores_deleted_items():
    """Test that soft-deleted items are not counted as children."""
    # Create a folder with children
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    child1 = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)

    # Soft delete one child
    child1.soft_delete()

    # Manually set wrong values
    parent.numchild = 10
    parent.numchild_folder = 5
    parent.save(update_fields=["numchild", "numchild_folder"])

    call_command("sync_item_numchild")

    # Refresh from database
    parent.refresh_from_db()

    # Should count only non-deleted children
    assert parent.numchild == 2  # 2 remaining children
    assert parent.numchild_folder == 1  # 1 folder child


def test_sync_item_numchild_ignores_deleted_parents():
    """Test that soft-deleted parent items are not processed."""
    # Create a folder with children
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)

    # Soft delete the parent
    parent.soft_delete()

    # Manually set wrong values
    models.Item.objects.filter(id=parent.id).update(numchild=10, numchild_folder=5)

    call_command("sync_item_numchild")

    # Refresh from database
    parent.refresh_from_db()

    # Values should not have been updated because parent is deleted
    assert parent.numchild == 10
    assert parent.numchild_folder == 5


def test_sync_item_numchild_nested_structure():
    """Test the command with a nested folder structure."""
    # Create nested structure: root -> folder1 -> folder2 -> file
    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    folder1 = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    folder2 = factories.ItemFactory(parent=folder1, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=folder2, type=models.ItemTypeChoices.FILE)
    factories.ItemFactory(parent=folder1, type=models.ItemTypeChoices.FILE)

    # Corrupt all values
    models.Item.objects.update(numchild=0, numchild_folder=0)

    call_command("sync_item_numchild")

    # Refresh all items
    root.refresh_from_db()
    folder1.refresh_from_db()
    folder2.refresh_from_db()

    # Check values
    assert root.numchild == 1  # only folder1 direct child
    assert root.numchild_folder == 1  # folder1

    assert folder1.numchild == 2  # folder2 and file2
    assert folder1.numchild_folder == 1  # folder2

    assert folder2.numchild == 1  # file1
    assert folder2.numchild_folder == 0  # no folders


def test_sync_item_numchild_no_updates_needed():
    """Test the command when all values are already correct."""
    # Create a folder with children (factory should set correct values)
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FILE)
    factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    # Verify values are already correct
    parent.refresh_from_db()
    assert parent.numchild == 2
    assert parent.numchild_folder == 1

    output = StringIO()
    call_command("sync_item_numchild", stdout=output)

    # Should indicate no updates were needed
    output_str = output.getvalue()
    assert "Successfully updated 0 items" in output_str


def test_sync_item_numchild_with_ancestors_deleted():
    """Test that items with deleted ancestors are not processed."""
    # Create nested structure
    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory(parent=child, type=models.ItemTypeChoices.FILE)

    # Delete parent (this sets ancestors_deleted_at on descendants)
    parent.soft_delete()

    # Manually corrupt child's values
    models.Item.objects.filter(id=child.id).update(numchild=10, numchild_folder=5)

    call_command("sync_item_numchild")

    # Child should not have been processed
    child.refresh_from_db()
    assert child.numchild == 10
    assert child.numchild_folder == 5
