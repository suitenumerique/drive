"""Tests for the per-user usage cache helpers."""

from unittest import mock

from core.storage.cache import invalidate_storage_used_cache


def test_invalidate_storage_used_cache_invalidates_entitlements():
    """The entitlements backend cache should be invalidated for the filtered user ids."""
    with mock.patch("core.entitlements.get_entitlements_backend") as mock_get_backend:
        invalidate_storage_used_cache(["user-1", None, "user-2"])

    mock_get_backend.return_value.invalidate_cache.assert_called_once_with(["user-1", "user-2"])


def test_invalidate_storage_used_cache_without_user_ids():
    """Nothing should be invalidated when no valid user id is given."""
    with mock.patch("core.entitlements.get_entitlements_backend") as mock_get_backend:
        invalidate_storage_used_cache([None])

    mock_get_backend.assert_not_called()
