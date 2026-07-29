"""Docs external app backend."""

import logging

import requests

from .base import ExternalAppBackend, ExternalAppError

logger = logging.getLogger(__name__)


class DocsExternalAppBackend(ExternalAppBackend):
    """Back-channel client for the Docs application."""

    def _post(self, path, payload):
        """POST to the Docs server-to-server API."""
        if not self.api_base_url or not self.token:
            raise ExternalAppError("Docs integration is not configured.")

        url = f"{self.api_base_url}{path}"
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ExternalAppError(f"Could not reach Docs: {exc}") from exc

        if response.status_code >= 400:
            raise ExternalAppError(
                f"Docs call failed ({response.status_code}) on {path}: "
                f"{response.text[:500]}"
            )

        return response.json()

    def create_resource(self, item, user):
        """Create the Docs document matching a freshly created external item."""
        return self._post(
            "/documents/create-for-owner/",
            {
                "id": str(item.id),
                "title": item.title,
                "sub": user.sub,
                "email": user.email,
            },
        )

    def delete_resources(self, item_ids):
        """Move the matching Docs documents to their soft-deleted state."""
        return self._post("/documents/s2s-delete/", {"ids": [str(i) for i in item_ids]})

    def restore_resources(self, item_ids):
        """Restore the matching soft-deleted Docs documents."""
        return self._post("/documents/s2s-restore/", {"ids": [str(i) for i in item_ids]})

    def purge_resources(self, item_ids):
        """Permanently destroy the matching Docs documents and their storage."""
        return self._post("/documents/s2s-purge/", {"ids": [str(i) for i in item_ids]})
