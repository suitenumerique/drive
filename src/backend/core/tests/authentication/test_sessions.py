"""Tests for the session store."""

from unittest import mock

from django.contrib.sessions.backends.cache import KEY_PREFIX
from django.core.cache import cache

import pytest
from redis.exceptions import TimeoutError as RedisTimeoutError
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


def test_sessions_cache_error_keeps_session():
    """A session the cache fails to read should raise instead of logging the user out."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    cache_get = cache.get

    def get(key, *args, **kwargs):
        if key.startswith(KEY_PREFIX):
            raise RedisTimeoutError("Timeout reading from socket")
        return cache_get(key, *args, **kwargs)

    with mock.patch.object(cache, "get", side_effect=get):
        with pytest.raises(RedisTimeoutError):
            client.get("/api/v1.0/users/me/")

    response = client.get("/api/v1.0/users/me/")
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
