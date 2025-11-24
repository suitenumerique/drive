"""Fixtures for tests in the drive wopi application"""

from django.core.cache import cache

import pytest

from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY


@pytest.fixture(autouse=True)
def clear_cache():
    """Fixture to clear the cache before each test."""
    yield
    cache.clear()


@pytest.fixture
def configure_wopi_clients():
    """Configure wopi clients."""

    wopi_configuration = {
        "mimetypes": {
            "text/plain": {
                "launch_url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            }
        },
        "extensions": {
            "txt": {
                "launch_url": "http://localhost:9980/browser/0968141f2c/cool.html?",
                "client": "vendorA",
            }
        },
        "vendorA": {
            "proof_keys": {"public_key": b"public_proof_key\n"},
        },
    }
    cache.set(WOPI_CONFIGURATION_CACHE_KEY, wopi_configuration)

    yield wopi_configuration
    cache.delete(WOPI_CONFIGURATION_CACHE_KEY)
