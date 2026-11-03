"""
Tests for the migration normalizing stored emails.
"""

from importlib import import_module

from django.apps import apps

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db

migration = import_module("core.migrations.0035_normalize_stored_emails")


def _user_with_stored_email(email, **kwargs):
    """Create a user storing the email as is, like the rows predating the normalization."""
    user = factories.UserFactory(**kwargs)
    models.User.objects.filter(pk=user.pk).update(email=email)
    return user


def _invitation_with_stored_email(item, email):
    """Create an invitation storing the email as is, like the rows predating the normalization."""
    invitation = factories.InvitationFactory(item=item)
    models.Invitation.objects.filter(pk=invitation.pk).update(email=email)
    return invitation


@pytest.mark.parametrize(
    "stored_email, expected_email",
    [
        ("John.Doe@Example.COM", "john.doe@example.com"),
        ("  john.doe@example.com ", "john.doe@example.com"),
        ("john.doe@example.com", "john.doe@example.com"),
        ("Jane.dısk@Example.com", "jane.dısk@example.com"),
        ("Jane.ſmith@Example.com", "jane.ſmith@example.com"),
        ("Kevin@Example.com", "Kevin@example.com"),
        ("", ""),
        (None, None),
    ],
)
def test_migrations_normalize_stored_emails_users(stored_email, expected_email):
    """Only the surrounding spaces and the ASCII case of user emails should change."""
    user = _user_with_stored_email(stored_email)

    migration.forwards(apps, None)

    user.refresh_from_db()
    assert user.email == expected_email


def test_migrations_normalize_stored_emails_users_duplicates_kept():
    """Users whose emails only differ by case should be kept and share the normalized email."""
    upper_user = _user_with_stored_email("John.Doe@example.com")
    lower_user = _user_with_stored_email("john.doe@example.com")

    migration.forwards(apps, None)

    upper_user.refresh_from_db()
    lower_user.refresh_from_db()
    assert upper_user.email == "john.doe@example.com"
    assert lower_user.email == "john.doe@example.com"


def test_migrations_normalize_stored_emails_users_admin_email_ignored():
    """The admin email of a user should not change."""
    user = _user_with_stored_email("john.doe@example.com", admin_email="Admin@Example.com")

    migration.forwards(apps, None)

    user.refresh_from_db()
    assert user.admin_email == "Admin@Example.com"


def test_migrations_normalize_stored_emails_invitations():
    """The email of an invitation should be normalized."""
    invitation = _invitation_with_stored_email(factories.ItemFactory(), " Guest@Example.com ")

    migration.forwards(apps, None)

    invitation.refresh_from_db()
    assert invitation.email == "guest@example.com"


@pytest.mark.parametrize(
    "old_email, new_email",
    [
        ("Guest@example.com", "guest@example.com"),
        ("guest@example.com", "Guest@example.com"),
        (" guest@example.com", "guest@example.com"),
    ],
)
def test_migrations_normalize_stored_emails_invitations_duplicates(old_email, new_email):
    """Only the most recent invitation of an item should remain for a normalized email."""
    item = factories.ItemFactory()
    _invitation_with_stored_email(item, old_email)
    new_invitation = _invitation_with_stored_email(item, new_email)

    migration.forwards(apps, None)

    assert list(models.Invitation.objects.values_list("id", "email")) == [
        (new_invitation.id, "guest@example.com")
    ]


def test_migrations_normalize_stored_emails_invitations_other_item_kept():
    """Invitations of different items should be kept for a same normalized email."""
    invitation = _invitation_with_stored_email(factories.ItemFactory(), "Guest@example.com")
    other_invitation = _invitation_with_stored_email(factories.ItemFactory(), "guest@example.com")

    migration.forwards(apps, None)

    assert set(models.Invitation.objects.values_list("id", "email")) == {
        (invitation.id, "guest@example.com"),
        (other_invitation.id, "guest@example.com"),
    }


def test_migrations_normalize_stored_emails_invitations_non_ascii_kept():
    """An invitation for an email differing by a non-ASCII letter should not be a duplicate."""
    item = factories.ItemFactory()
    invitation = _invitation_with_stored_email(item, "alice@example.com")
    non_ascii_invitation = _invitation_with_stored_email(item, "alıce@example.com")

    migration.forwards(apps, None)

    assert set(models.Invitation.objects.values_list("id", "email")) == {
        (invitation.id, "alice@example.com"),
        (non_ascii_invitation.id, "alıce@example.com"),
    }
