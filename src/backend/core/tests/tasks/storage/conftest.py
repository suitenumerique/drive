"""Fixtures for tests in the core.tests.tasks.storage module."""

import pytest

from core.tasks.storage import get_mirror_s3_client


@pytest.fixture(autouse=True)
def clear_get_mirror_s3_client_cache():
    """Clear the cache for get_mirror_s3_client."""
    get_mirror_s3_client.cache_clear()
