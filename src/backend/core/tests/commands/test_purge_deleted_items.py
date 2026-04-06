"""Tests for the purge_deleted_items management command."""

from datetime import timedelta
from io import BytesIO, StringIO
from random import randint
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.utils import timezone

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_purge_deleted_items_no_deleted_items(django_assert_num_queries):
    """Nothing happens when there are no purgeable items."""
    with django_assert_num_queries(1):
        call_command("purge_deleted_items")


# pylint: disable=too-many-statements
def test_purge_deleted_items_success(settings):  # noqa: PLR0915
    """
    Ensure the purge command deletes:
    - hard-deleted items
    - soft-deleted items whose retention period has expired

    The expiry delay is computed from settings (TRASHBIN_CUTOFF_DAYS + PURGE_GRACE_DAYS),
    which must remain configurable. This test verifies behavior against those settings
    by simulating items deleted at different points in time.
    """
    out = StringIO()

    settings.TRASHBIN_CUTOFF_DAYS = cutoff = randint(0, 50)
    settings.PURGE_GRACE_DAYS = grace = randint(0, 20)

    now = timezone.now()
    purge_now = now - timedelta(days=cutoff + grace)

    # 1- Not deleted
    not_deleted_file = factories.ItemFactory(type=models.ItemTypeChoices.FILE)
    default_storage.save(not_deleted_file.file_key, BytesIO(b"data"))

    not_deleted_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    not_deleted_child = factories.ItemFactory(
        parent=not_deleted_parent,
        type=models.ItemTypeChoices.FILE,
    )
    default_storage.save(not_deleted_child.file_key, BytesIO(b"data"))

    # 2- Soft deleted, not purgeable
    with patch("django.utils.timezone.now", return_value=now):
        not_purgeable_file = factories.ItemFactory(type=models.ItemTypeChoices.FILE)
        default_storage.save(not_purgeable_file.file_key, BytesIO(b"data"))
        not_purgeable_file.soft_delete()

        not_purgeable_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
        not_purgeable_child = factories.ItemFactory(
            parent=not_purgeable_parent,
            type=models.ItemTypeChoices.FILE,
        )
        default_storage.save(not_purgeable_child.file_key, BytesIO(b"data"))
        not_purgeable_parent.soft_delete()

    # 3- Soft deleted, purgeable
    with patch("django.utils.timezone.now", return_value=purge_now):
        purgeable_file = factories.ItemFactory(type=models.ItemTypeChoices.FILE)
        default_storage.save(purgeable_file.file_key, BytesIO(b"data"))
        purgeable_file.soft_delete()

        purgeable_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
        purgeable_child = factories.ItemFactory(
            parent=purgeable_parent,
            type=models.ItemTypeChoices.FILE,
        )
        default_storage.save(purgeable_child.file_key, BytesIO(b"data"))
        purgeable_parent.soft_delete()

    # 4- Hard deleted
    hard_deleted_file = factories.ItemFactory(type=models.ItemTypeChoices.FILE)
    default_storage.save(hard_deleted_file.file_key, BytesIO(b"data"))
    hard_deleted_file.soft_delete()
    hard_deleted_file.hard_delete()

    hard_deleted_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    hard_deleted_child = factories.ItemFactory(
        parent=hard_deleted_parent,
        type=models.ItemTypeChoices.FILE,
    )
    default_storage.save(hard_deleted_child.file_key, BytesIO(b"data"))
    hard_deleted_parent.soft_delete()
    hard_deleted_parent.hard_delete()

    # Run command
    call_command("purge_deleted_items", stdout=out)

    assert "Purged 5 deleted item(s)." in out.getvalue()

    # Database checks
    assert models.Item.objects.filter(id=not_deleted_file.id).exists()

    assert models.Item.objects.filter(id=not_purgeable_file.id).exists()

    assert not models.Item.objects.filter(id=purgeable_file.id).exists()

    assert not models.Item.objects.filter(id=hard_deleted_file.id).exists()

    assert models.Item.objects.filter(id=not_deleted_parent.id).exists()
    assert models.Item.objects.filter(id=not_deleted_child.id).exists()

    assert models.Item.objects.filter(id=not_purgeable_parent.id).exists()
    assert models.Item.objects.filter(id=not_purgeable_child.id).exists()

    assert not models.Item.objects.filter(id=purgeable_parent.id).exists()
    assert not models.Item.objects.filter(id=purgeable_child.id).exists()

    assert not models.Item.objects.filter(id=hard_deleted_parent.id).exists()
    assert not models.Item.objects.filter(id=hard_deleted_child.id).exists()

    # Storage checks
    assert default_storage.exists(not_deleted_file.file_key)
    assert default_storage.exists(not_purgeable_file.file_key)
    assert not default_storage.exists(purgeable_file.file_key)
    assert not default_storage.exists(hard_deleted_file.file_key)

    assert default_storage.exists(not_deleted_child.file_key)
    assert default_storage.exists(not_purgeable_child.file_key)
    assert not default_storage.exists(purgeable_child.file_key)
    assert not default_storage.exists(hard_deleted_child.file_key)
