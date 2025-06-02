"""
This service is used to relay events from the SDK to the backend.
"""

from django.conf import settings
from django.core.cache import cache

class SDKRelayManager:
    """
    This service is used to relay events from the SDK to the backend.
    """

    def _get_cache_key(self, token):
        """
        Get the cache key for the given token.
        """
        return f"sdk_relay:{token}"

    def register_event(self, token, event):
        """
        Register an event for the given token.
        """
        cache.set(
            self._get_cache_key(token),
            event,
            timeout=settings.SDK_RELAY_CACHE_TIMEOUT,
        )

    def get_event(self, token):
        """
        Get the event for the given token.
        """
        cache_key = self._get_cache_key(token)
        data = cache.get(cache_key)

        if not data:
            return {}

        cache.delete(cache_key)

        return data