"""Fixtures for tests in the drive wopi application"""

from django.core.cache import cache

import pytest


@pytest.fixture(autouse=True)
def clear_cache():
    """Fixture to clear the cache before each test."""
    yield
    cache.clear()
