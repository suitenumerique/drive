"""Entitlements backend utilities."""

from core.entitlements.factory import get_entitlements_backend


class EntitlementsUnavailableError(Exception):
    """Raised when the entitlements service is unavailable."""


__all__ = ["get_entitlements_backend", "EntitlementsUnavailableError"]
