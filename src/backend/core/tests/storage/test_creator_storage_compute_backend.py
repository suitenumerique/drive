"""
Tests for the CreatorStorageComputeBackend.
"""

import pytest

from core import factories, models
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


def test_storage_used_expression_matches_compute_storage_used():
    """The annotation should give each user the storage computed by compute_storage_used."""
    user = factories.UserFactory()
    factories.ItemFactory(creator=user, size=100)
    factories.ItemFactory(creator=user, size=250, quota_excluded=True)
    hard_deleted = factories.ItemFactory(creator=user, size=500)
    hard_deleted.soft_delete()
    hard_deleted.hard_delete()
    other = factories.UserFactory()
    factories.ItemFactory(creator=other, size=999)
    empty = factories.UserFactory()

    backend = CreatorStorageComputeBackend()
    storage_used = dict(
        models.User.objects.annotate(storage_used=backend.storage_used_expression()).values_list(
            "id", "storage_used"
        )
    )

    assert storage_used == {
        user.id: 100,
        other.id: 999,
        empty.id: 0,
    }
    for each in (user, other, empty):
        assert storage_used[each.id] == backend.compute_storage_used([each])
