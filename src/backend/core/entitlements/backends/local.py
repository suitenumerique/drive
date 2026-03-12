"""Local Entitlements Backend."""

from core.entitlements.backends.base import EntitlementsBackend


class LocalEntitlementsBackend(EntitlementsBackend):
    """Local entitlements backend for development and testing. Always grants access."""

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
