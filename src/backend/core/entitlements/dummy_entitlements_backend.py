"""
Dummy Entitlements Backend.
"""

from core.entitlements.entitlements_backend import EntitlementsBackend


class DummyEntitlementsBackend(EntitlementsBackend):
    """Dummy entitlements backend for testing purposes."""

    def can_access(self, user):
        """
        Check if a user can access app.
        """
        return {"result": True}

    def can_upload(self, user):
        """
        Check if a user can upload a file.
        """
        return {"result": True}
