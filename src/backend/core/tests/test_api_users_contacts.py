"""Tests for the users contacts API endpoint."""

import datetime

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def _login():
    """Create a user and return it with an authenticated API client."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    return user, client


def assert_contacts(response, *users):
    """Assert the response lists exactly the given users as contacts, in order."""
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(user.id),
            "full_name": user.full_name,
            "short_name": user.short_name,
        }
        for user in users
    ]


def test_api_users_contacts_anonymous():
    """Anonymous users should not be allowed to list their contacts."""
    client = APIClient()
    response = client.get("/api/v1.0/users/contacts/")
    assert response.status_code == 401


def test_api_users_contacts():
    """
    Contacts are users sharing items with the current user, most frequent first.
    """
    user, client = _login()

    alice = factories.UserFactory()
    bob = factories.UserFactory()
    charlie = factories.UserFactory()

    # Items shared with the current user.
    factories.ItemFactory.create_batch(2, users=[user, alice], creator=user)
    factories.ItemFactory(users=[user, bob], creator=user)
    # Items only bob has access to must not inflate his frequency.
    factories.ItemFactory.create_batch(3, users=[bob])
    # Charlie shares nothing with the current user.
    factories.ItemFactory(users=[charlie])

    response = client.get("/api/v1.0/users/contacts/")

    assert_contacts(response, alice, bob)


def test_api_users_contacts_frequency_includes_created_items():
    """Created items should count toward a contact's frequency ranking."""
    user, client = _login()

    alice = factories.UserFactory()
    bob = factories.UserFactory()

    # Alice shares 1 item with the user via access.
    factories.ItemFactory(users=[user, alice], creator=user)
    # Bob created 2 items the user has access to, but holds no access himself.
    factories.ItemFactory(users=[user], creator=bob)
    factories.ItemFactory(users=[user], creator=bob)

    response = client.get("/api/v1.0/users/contacts/")

    # Bob should rank first: 2 created items > 1 shared access.
    assert_contacts(response, bob, alice)


def test_api_users_contacts_excludes_inactive():
    """Inactive users should not appear in the contacts list."""
    user, client = _login()

    inactive = factories.UserFactory(is_active=False)
    factories.ItemFactory(users=[user, inactive], creator=user)

    response = client.get("/api/v1.0/users/contacts/")

    assert_contacts(response)


def test_api_users_contacts_without_sharing():
    """A user sharing no item with anybody should get an empty contacts list."""
    user, client = _login()

    factories.ItemFactory(users=[user], creator=user)

    response = client.get("/api/v1.0/users/contacts/")

    assert_contacts(response)


def test_api_users_contacts_excludes_deleted_items():
    """
    Contacts sharing only deleted items should not appear, as the contact filter
    would return nothing for them.
    """
    user, client = _login()

    now = datetime.datetime.now(tz=datetime.UTC)
    alice = factories.UserFactory()
    ghost = factories.UserFactory()
    spectre = factories.UserFactory()

    # Alive item shared with alice.
    factories.ItemFactory(users=[user, alice], creator=user)
    # Hard deleted item shared with ghost.
    hard_deleted = factories.ItemFactory(users=[user, ghost], creator=user)
    models.Item.objects.filter(pk=hard_deleted.pk).update(hard_deleted_at=now)
    # Trashed item shared with spectre.
    factories.ItemFactory(users=[user, spectre], deleted_at=now, creator=user)

    response = client.get("/api/v1.0/users/contacts/")

    assert_contacts(response, alice)


def test_api_users_contacts_via_team(mock_user_teams):
    """Contacts reached through a team-shared item should be listed too."""
    user, client = _login()

    mock_user_teams.return_value = ["team1"]

    alice = factories.UserFactory()
    # Item the current user reaches through "team1", with alice as a direct member.
    item = factories.TeamItemAccessFactory(team="team1", item__creator=user).item
    factories.UserItemAccessFactory(item=item, user=alice)

    response = client.get("/api/v1.0/users/contacts/")

    assert_contacts(response, alice)


def test_api_users_contacts_includes_item_creators():
    """People who shared an item (its creator) should appear in the contacts list."""
    user, client = _login()

    bob = factories.UserFactory()
    # Item created and shared by bob, visible to the user, but bob has no direct access.
    factories.ItemFactory(users=[user], creator=bob)

    response = client.get("/api/v1.0/users/contacts/")

    assert_contacts(response, bob)


def test_api_users_contacts_search():
    """The q parameter should filter contacts by email trigram similarity."""
    user, client = _login()

    alice = factories.UserFactory(email="alice@example.com")
    bob = factories.UserFactory(email="bob@example.com")

    factories.ItemFactory(users=[user, alice], creator=user)
    factories.ItemFactory(users=[user, bob], creator=user)

    response = client.get("/api/v1.0/users/contacts/?q=alice")

    assert_contacts(response, alice)


def test_api_users_contacts_search_no_match():
    """The q parameter should return an empty list when no contact matches."""
    user, client = _login()

    alice = factories.UserFactory(email="alice@example.com")
    factories.ItemFactory(users=[user, alice], creator=user)

    response = client.get("/api/v1.0/users/contacts/?q=zzzzz")

    assert_contacts(response)


def test_api_users_contacts_search_by_email():
    """The q parameter should match contacts by Levenshtein distance on email."""
    user, client = _login()

    alice = factories.UserFactory(email="alice@example.com")
    bob = factories.UserFactory(email="bob@example.com")

    factories.ItemFactory(users=[user, alice], creator=user)
    factories.ItemFactory(users=[user, bob], creator=user)

    # Exact match
    response = client.get("/api/v1.0/users/contacts/?q=alice@example.com")
    assert_contacts(response, alice)

    # Typo within Levenshtein distance 3
    response = client.get("/api/v1.0/users/contacts/?q=alce@example.com")
    assert_contacts(response, alice)

    # Too many typos (distance > 3)
    response = client.get("/api/v1.0/users/contacts/?q=zzzz@zzzzzzz.com")
    assert_contacts(response)


def test_api_users_contacts_limit(settings):
    """The contacts endpoint should respect the API_USERS_LIST_LIMIT setting."""
    user, client = _login()

    settings.API_USERS_LIST_LIMIT = 3
    for i in range(5):
        contact = factories.UserFactory(email=f"contact.{i}@example.com")
        factories.ItemFactory(users=[user, contact], creator=user)

    response = client.get("/api/v1.0/users/contacts/")

    assert response.status_code == 200
    assert len(response.json()) == 3
