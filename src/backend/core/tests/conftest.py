"""Fixtures for tests in the drive core application"""

from unittest import mock

from django.core.cache import cache

import pytest

USER = "user"
TEAM = "team"
VIA = [USER, TEAM]


@pytest.fixture(autouse=True)
def clear_cache():
    """Fixture to clear the cache after each test."""
    yield
    cache.clear()


@pytest.fixture
def mock_user_teams():
    """Mock for the "teams" property on the User model."""
    with mock.patch(
        "core.models.User.teams", new_callable=mock.PropertyMock
    ) as mock_teams:
        yield mock_teams
