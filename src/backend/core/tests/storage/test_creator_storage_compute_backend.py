"""
Tests for the CreatorStorageComputeBackend.
"""

import pytest

from core import factories
from core.storage.creator_storage_compute_backend import CreatorStorageComputeBackend

pytestmark = pytest.mark.django_db


def test_compute_storage_used_sums_creator_items():
    """The backend should sum the sizes of all items created by the given users."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=100)
    factories.ItemFactory(creator=user, size=250)
    factories.ItemFactory(size=999)  # another creator, should not count

    assert CreatorStorageComputeBackend().compute_storage_used([user]) == 350


def test_compute_storage_used_excludes_hard_deleted_items():
    """Hard-deleted items should not count toward the storage used."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=100)
    hard_deleted = factories.ItemFactory(creator=user, size=250)
    hard_deleted.soft_delete()
    hard_deleted.hard_delete()

    assert CreatorStorageComputeBackend().compute_storage_used([user]) == 100


def test_compute_storage_used_keeps_soft_deleted_items():
    """Soft-deleted (trashbin) items should still count toward the storage used."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=100)
    soft_deleted = factories.ItemFactory(creator=user, size=250)
    soft_deleted.soft_delete()

    assert CreatorStorageComputeBackend().compute_storage_used([user]) == 350


def test_compute_storage_used_excludes_quota_excluded_items():
    """Items flagged as quota excluded should not count toward the storage used."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=100)
    factories.ItemFactory(creator=user, size=250, quota_excluded=True)

    assert CreatorStorageComputeBackend().compute_storage_used([user]) == 100


def test_compute_storage_used_only_quota_excluded_items():
    """A user owning only quota excluded items should have a storage used of zero."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=100, quota_excluded=True)
    factories.ItemFactory(creator=user, size=250, quota_excluded=True)

    assert CreatorStorageComputeBackend().compute_storage_used([user]) == 0
