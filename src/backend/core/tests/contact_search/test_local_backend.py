"""The local backend: Drive's active users, matched on their email."""

import pytest

from core import factories
from core.contact_search import LocalContactSearchBackend

pytestmark = pytest.mark.django_db


def test_short_queries_find_nobody(user):
    """Less than 5 characters: nothing, so nobody can list the users."""
    factories.UserFactory(email="john.doe@example.org")

    assert not LocalContactSearchBackend().search(user, "john", limit=5)


def test_users_are_found_by_email(user):
    """A query close to an email finds the active user."""
    john = factories.UserFactory(email="john.doe@example.org", full_name="John Doe")
    factories.UserFactory(email="john.doe@other.org", is_active=False)

    results = LocalContactSearchBackend().search(user, "john.doe@example.org", limit=5)

    assert [(result.kind, result.user, result.email, result.name) for result in results] == [
        ("user", john, "john.doe@example.org", "John Doe")
    ]
