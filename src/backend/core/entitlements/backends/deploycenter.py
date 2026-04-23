"""DeployCenter Entitlements Backend."""

import logging

from django.core.cache import cache

import requests

from core.entitlements.backends.base import EntitlementsBackend

logger = logging.getLogger(__name__)

ENTITLEMENTS_CACHE_TIMEOUT = 60
ENTITLEMENTS_CACHE_KEY_PREFIX = "entitlements:user:"


class DeployCenterEntitlementsBackend(EntitlementsBackend):
    """Entitlements backend that checks permissions via a DeployCenter service."""

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(self, base_url, service_id, api_key, cache_timeout=10, oidc_claims=None):
        self.base_url = base_url
        self.service_id = service_id
        self.api_key = api_key
        self.cache_timeout = cache_timeout
        self.oidc_claims = oidc_claims or []

    def fetch_entitlements(self, user):
        """Fetch entitlements for a user from the DeployCenter service."""
        params = {
            "account_type": "user",
            "account_email": user.email,
            "service_id": self.service_id,
        }
        for claim in self.oidc_claims:
            value = user.claims.get(claim)
            if value is not None:
                params[claim] = value

        response = requests.get(
            self.base_url,
            params=params,
            headers={"X-Service-Auth": f"Bearer {self.api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_entitlements(self, user):
        """Get entitlements for a user, cached."""
        cache_key = f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user.id}"
        entitlements = cache.get(cache_key)
        if entitlements:
            return entitlements
        try:
            entitlements = self.fetch_entitlements(user)
        except requests.RequestException:
            logger.exception("Failed to fetch entitlements for user %s", user.id)
            raise
        cache.set(cache_key, entitlements, timeout=self.cache_timeout)
        return entitlements

    def get_context(self, user):
        """Get context for a user."""
        attributes_whitelist = ["organization", "operator", "potentialOperators"]
        entitlements = self.get_entitlements(user)
        context = {}
        for attribute in attributes_whitelist:
            context[attribute] = entitlements.get(attribute)
        return context

    def can_upload(self, user):
        """Check if a user can upload a file."""
        entitlements = self.get_entitlements(user)
        return {
            "result": entitlements.get("entitlements", {}).get("can_upload", False),
            "reason": entitlements.get("entitlements", {}).get("can_upload_reason", None),
        }

    def can_access(self, user):
        """Check if a user can access the app."""
        entitlements = self.get_entitlements(user)
        return {"result": entitlements.get("entitlements", {}).get("can_access", False)}
