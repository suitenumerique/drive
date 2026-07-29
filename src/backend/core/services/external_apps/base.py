"""External app backend base class."""

from abc import ABC, abstractmethod


class ExternalAppError(Exception):
    """Raised when a call to an external app fails."""


class ExternalAppBackend(ABC):
    """
    Abstract base class for external app backends.

    An external app owns the physical resources that Drive items of type FILE
    with `metadata.external_app == <name>` point to. Drive owns the tree,
    sharing and trash; the backend keeps the external app's resources in sync
    with the lifecycle of their pointer items.
    """

    def __init__(self, name, api_base_url, token, frontend_url=None, timeout=10, **kwargs):
        self.name = name
        self.api_base_url = api_base_url.rstrip("/") if api_base_url else None
        self.token = token
        self.frontend_url = frontend_url
        self.timeout = timeout

    @abstractmethod
    def create_resource(self, item, user):
        """
        Create the external resource backing `item` on behalf of `user`.
        Returns the created payload.
        """

    def delete_resources(self, item_ids):
        """Soft-delete the external resources for the given item ids. No-op by default."""

    def restore_resources(self, item_ids):
        """Restore soft-deleted external resources. No-op by default."""

    def purge_resources(self, item_ids):
        """Permanently destroy external resources and their storage. No-op by default."""
