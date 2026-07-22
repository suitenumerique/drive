"""Entitlements Backend base class."""

from abc import ABC, abstractmethod
from enum import StrEnum


class QuotaState(StrEnum):
    """State of a quota gauge returned by get_quota."""

    DEFAULT = "default"
    EXCEEDED_LOCKED = "exceeded_locked"
    ERROR = "error"


class QuotaReason(StrEnum):
    """Reasons explaining why the quota gauge is locked (get_quota output)."""

    ORGANIZATION_QUOTA_EXCEEDED = "organization_quota_exceeded"


class CanUploadReason(StrEnum):
    """Reasons explaining why a user cannot upload (can_upload output)."""

    NO_ORGANIZATION = "no_organization"
    NOT_ACTIVATED = "not_activated"
    USER_QUOTA_EXCEEDED = "user_quota_exceeded"
    USER_OVERRIDE_QUOTA_EXCEEDED = "user_override_quota_exceeded"
    ORGANIZATION_QUOTA_EXCEEDED = "organization_quota_exceeded"


class QuotaError(StrEnum):
    """Errors that can occur while computing a quota."""

    METRIC_ACCOUNT_NOT_FOUND = "metric_account_not_found"
    MAX_STORAGE_ACCOUNT_NOT_FOUND = "max_storage_account_not_found"


class EntitlementsBackend(ABC):
    """Abstract base class for entitlements backends."""

    @abstractmethod
    def can_access(self, user):
        """
        Check if a user can access app.
        """

    @abstractmethod
    def can_upload(self, user):
        """
        Check if a user can upload a file.
        """

    def get_context(self, user):  # pylint: disable=unused-argument
        """Get context for a user."""
        return {}

    def get_quota(self, user):  # pylint: disable=unused-argument
        """Get quota for a user."""
        return {}

    def invalidate_cache(self, user_ids):  # noqa: B027
        """Invalidate any cached entitlements for these users. No-op by default."""
