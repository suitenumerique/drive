"""Services for the WOPI lock operations."""

from django.conf import settings
from django.core.cache import cache

from core.models import Item
from core.utils.no_leak import sha256_16


class LockService:
    """Service for the WOPI lock operations."""

    lock_timeout = settings.WOPI_LOCK_TIMEOUT
    lock_prefix = "wopi_lock"

    def __init__(self, item: Item):
        self.item = item

    @property
    def _lock_key(self):
        """Get the lock key for the item."""
        return f"{self.lock_prefix}:{self.item.id}"

    def lock(self, lock_value: str):
        """Lock the item."""
        cache.set(self._lock_key, lock_value, timeout=self.lock_timeout)

    def get_lock(self, default: str = None):
        """Get the lock."""
        return cache.get(self._lock_key, default)

    def refresh_lock(self):
        """Refresh the lock."""
        cache.touch(self._lock_key, timeout=self.lock_timeout)

    def is_locked(self):
        """Check if the item is locked."""
        return self.get_lock() is not None

    def is_lock_valid(self, lock_value: str):
        """Check if the lock is valid."""
        return cache.get(self._lock_key) == lock_value

    def unlock(self):
        """Unlock the item."""
        cache.delete(self._lock_key)


class MountLockService:
    """Cache-backed WOPI lock service for mount entries (no-leak keys)."""

    lock_timeout = settings.WOPI_LOCK_TIMEOUT
    lock_prefix = "wopi_mount_lock"

    def __init__(self, *, mount_id: str, normalized_path: str):
        self.mount_id = str(mount_id or "").strip()
        self._path_hash = sha256_16(str(normalized_path or ""))

    @property
    def _lock_key(self) -> str:
        """Return the cache key for the mount lock (hashed path)."""
        return f"{self.lock_prefix}:{self.mount_id}:{self._path_hash}"

    def lock(self, lock_value: str) -> None:
        """Acquire a lock with a deterministic TTL."""
        cache.set(self._lock_key, lock_value, timeout=self.lock_timeout)

    def get_lock(self, default: str = None):
        """Return the current lock value (or default when missing)."""
        return cache.get(self._lock_key, default)

    def refresh_lock(self) -> None:
        """Refresh the lock TTL without changing its value."""
        cache.touch(self._lock_key, timeout=self.lock_timeout)

    def is_locked(self) -> bool:
        """Return whether a lock exists."""
        return self.get_lock() is not None

    def is_lock_valid(self, lock_value: str) -> bool:
        """Return whether the current lock matches the provided value."""
        return cache.get(self._lock_key) == lock_value

    def unlock(self) -> None:
        """Release the lock."""
        cache.delete(self._lock_key)
