"""Local Entitlements Backend."""

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.entitlements.backends.base import (
    CanUploadReason,
    EntitlementsBackend,
    QuotaState,
)
from core.storage import get_storage_compute_backend
from core.storage.cache import get_storage_used_cache_key

DEFAULT_STORAGE_LIMIT = 10 * 1024**3  # 10 GiB
DEFAULT_CACHE_TIMEOUT = 3600


class LocalEntitlementsBackend(EntitlementsBackend):
    """
    Entitlements backend enforcing per-user storage limits from local data.

    Every user gets a default storage limit, overridable per user via the
    ``storage_limit_override`` field on the User model (null: use the default
    limit, 0: unlimited). Users created before ``exempt_users_created_before``
    and without an override are exempted from any limit.

    The quota is soft: ``can_upload`` is checked before the file size is
    known, so a single upload can overshoot the limit; the next one is then
    blocked.
    """

    def __init__(
        self,
        default_storage_limit=DEFAULT_STORAGE_LIMIT,
        exempt_users_created_before=None,
        cache_timeout=DEFAULT_CACHE_TIMEOUT,
    ):
        self.default_storage_limit = int(default_storage_limit)
        if self.default_storage_limit <= 0:
            raise ImproperlyConfigured(
                "LocalEntitlementsBackend: 'default_storage_limit' must be a "
                "positive number of bytes."
            )

        self.cache_timeout = int(cache_timeout)
        if self.cache_timeout <= 0:
            raise ImproperlyConfigured(
                "LocalEntitlementsBackend: 'cache_timeout' must be a positive number of seconds."
            )

        self.exempt_users_created_before = None
        if exempt_users_created_before is not None:
            parsed = parse_datetime(str(exempt_users_created_before))
            if parsed is None:
                raise ImproperlyConfigured(
                    "LocalEntitlementsBackend: 'exempt_users_created_before' must "
                    "be an ISO 8601 datetime string."
                )
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed)
            self.exempt_users_created_before = parsed

    def get_storage_limit(self, user):
        """
        Return the effective storage limit in bytes for a user, or None if the
        user has no limit. The per-user override always takes precedence over
        the exemption cutoff.
        """
        override = getattr(user, "storage_limit_override", None)
        if override is not None:
            return None if override == 0 else override

        if (
            self.exempt_users_created_before is not None
            and user.created_at < self.exempt_users_created_before
        ):
            return None

        return self.default_storage_limit

    def get_storage_used(self, user):
        """
        Get the storage currently used by a user, cached.

        The cached value is invalidated whenever an item write changes the
        user's usage; the timeout is only a safety net against stale values.
        """
        cache_key = get_storage_used_cache_key(user.id)
        usage = cache.get(cache_key)
        if usage is None:
            usage = get_storage_compute_backend().compute_storage_used([user])
            cache.set(cache_key, usage, timeout=self.cache_timeout)
        return usage

    def can_access(self, user):
        """Check if a user can access the app."""
        return {"result": True}

    def can_upload(self, user):
        """Check if a user can upload a file."""
        if not user.is_authenticated:
            return {"result": False}

        limit = self.get_storage_limit(user)
        if limit is None:
            return {"result": True}

        if self.get_storage_used(user) >= limit:
            override_set = getattr(user, "storage_limit_override", None) is not None
            return {
                "result": False,
                "reason": (
                    CanUploadReason.USER_OVERRIDE_QUOTA_EXCEDEED
                    if override_set
                    else CanUploadReason.USER_QUOTA_EXCEDEED
                ),
                "message": "You have exceeded your storage limit.",
            }

        return {"result": True}

    def get_quota(self, user):
        """Get quota for a user."""
        if not user.is_authenticated:
            return {}

        limit = self.get_storage_limit(user)
        # Unlimited users (override set to 0 or exempted): do not render the gauge.
        if limit is None:
            return {}

        return {
            "state": QuotaState.DEFAULT,
            "usage": self.get_storage_used(user),
            "limit": limit,
        }
