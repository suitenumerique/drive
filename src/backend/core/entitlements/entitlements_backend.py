"""
Entitlements Backend.
"""

from abc import ABC, abstractmethod


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
