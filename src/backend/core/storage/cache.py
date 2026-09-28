"""Cache helpers for per-user storage usage values."""

from django.core.cache import cache

STORAGE_USED_CACHE_KEY_PREFIX = "storage_used:user:"


def get_storage_used_cache_key(user_id):
    """Build the cache key holding the storage used by a user."""
    return f"{STORAGE_USED_CACHE_KEY_PREFIX}{user_id}"


def invalidate_storage_used_cache(user_ids):
    """Invalidate the per-user usage caches (storage used + entitlements)."""
    user_ids = [user_id for user_id in user_ids if user_id]
    if not user_ids:
        return
    cache.delete_many([get_storage_used_cache_key(user_id) for user_id in user_ids])
    # Imported lazily: the local entitlements backend imports this module.
    # pylint: disable-next=import-outside-toplevel
    from core.entitlements import get_entitlements_backend  # noqa: PLC0415

    get_entitlements_backend().invalidate_cache(user_ids)
