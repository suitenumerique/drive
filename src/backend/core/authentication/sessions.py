"""Session store of the Drive application."""

from django.contrib.sessions.backends.cache import SessionStore as CacheSessionStore


class SessionStore(CacheSessionStore):
    """Store the sessions in the cache, without logging users out when it fails."""

    def load(self):
        """Load the session, raising the cache errors instead of resetting it."""
        # Django resets the session on any cache error, so the session middleware
        # would delete the cookie of a user only hit by a slow or down Redis
        session_data = self._cache.get(self.cache_key)
        if session_data is not None:
            return session_data
        self._session_key = None
        return {}
