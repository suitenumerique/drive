"""Fixtures for tests in the drive wopi application"""

from django.core.cache import cache

import pytest

from wopi.services.s3_prerequisites import WOPI_S3_BUCKET_VERSIONING_CACHE_KEY


@pytest.fixture(autouse=True)
def clear_cache():
    """Fixture to clear the cache before each test."""
    cache.set(
        WOPI_S3_BUCKET_VERSIONING_CACHE_KEY,
        {
            "ok": True,
            "status": "Enabled",
            "failure_class": None,
            "next_action_hint": None,
            "evidence": {"s3_backend_available": True},
        },
    )
    yield
    cache.clear()
