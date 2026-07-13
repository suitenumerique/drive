"""DeployCenter Entitlements Backend."""

import logging

from django.core.cache import cache

import requests

from core.entitlements.backends.base import (
    CanUploadReason,
    EntitlementsBackend,
    QuotaError,
    QuotaReason,
    QuotaState,
)

logger = logging.getLogger(__name__)

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

    def invalidate_cache(self, user_ids):
        """Drop cached entitlements so the next read refetches from DeployCenter."""
        cache.delete_many([f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user_id}" for user_id in user_ids])

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
        result = entitlements.get("entitlements", {}).get("can_upload", False)
        reason = entitlements.get("entitlements", {}).get("can_upload_reason", None)
        resolve_level = entitlements.get("entitlements", {}).get("can_upload_resolve_level", None)

        actual_reason = reason
        if not actual_reason and not result:
            if resolve_level == "user":
                actual_reason = CanUploadReason.USER_QUOTA_EXCEDEED
            elif resolve_level == "user_override":
                actual_reason = CanUploadReason.USER_OVERRIDE_QUOTA_EXCEDEED
            elif resolve_level == "organization":
                actual_reason = CanUploadReason.ORGANIZATION_QUOTA_EXCEDEED

        return {
            "result": result,
            "reason": actual_reason,
        }

    def can_access(self, user):
        """Check if a user can access the app."""
        entitlements = self.get_entitlements(user)
        return {"result": entitlements.get("entitlements", {}).get("can_access", False)}

    def get_quota(self, user):
        """Get quota for a user."""
        if not user.is_authenticated:
            return {}

        entitlements = self.get_entitlements(user)
        can_upload = entitlements.get("entitlements", {}).get("can_upload", False)
        can_upload_resolve_level = entitlements.get("entitlements", {}).get(
            "can_upload_resolve_level", False
        )
        can_upload_reason = entitlements.get("entitlements", {}).get("can_upload_reason", None)

        # Means that the service is not enabled in the user's organization or
        # the user does not have organization.
        # Do not render the gauge.
        if not can_upload and can_upload_reason in [
            CanUploadReason.NO_ORGANIZATION,
            CanUploadReason.NOT_ACTIVATED,
        ]:
            return {}

        max_storage_organization = entitlements.get("entitlements", {}).get(
            "max_storage_organization", {}
        )
        # Means that the user's organization has reached the quota.
        if (
            not can_upload
            and max_storage_organization
            and can_upload_resolve_level == "organization"
        ):
            return {
                "state": QuotaState.EXCEDEED_LOCKED,
                "reason": QuotaReason.ORGANIZATION_QUOTA_EXCEDEED,
            }

        metric_account = entitlements.get("metrics", {}).get("account", {})
        max_storage_account = entitlements.get("entitlements", {}).get("max_storage_account")

        if not metric_account:
            return {
                "state": QuotaState.ERROR,
                "error": QuotaError.METRIC_ACCOUNT_NOT_FOUND,
            }

        if max_storage_account is None:
            return {
                "state": QuotaState.ERROR,
                "error": QuotaError.MAX_STORAGE_ACCOUNT_NOT_FOUND,
            }

        return {
            "state": QuotaState.DEFAULT,
            "usage": metric_account.get("storage_used", 0),
            "limit": max_storage_account,
        }
