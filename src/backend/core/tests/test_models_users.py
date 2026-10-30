"""
Unit tests for the User model
"""

from unittest import mock

from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_users_str():
    """The str representation should be the email."""
    user = factories.UserFactory()
    assert str(user) == user.email


def test_models_users_id_unique():
    """The "id" field should be unique."""
    user = factories.UserFactory()
    with pytest.raises(ValidationError, match="User with this Id already exists."):
        factories.UserFactory(id=user.id)


def test_models_users_send_mail_main_existing():
    """The "email_user' method should send mail to the user's email address."""
    user = factories.UserFactory()

    with mock.patch("django.core.mail.send_mail") as mock_send:
        user.email_user("my subject", "my message")

    mock_send.assert_called_once_with("my subject", "my message", None, [user.email])


def test_models_users_send_mail_main_missing():
    """The "email_user' method should fail if the user has no email address."""
    user = factories.UserFactory(email=None)

    with pytest.raises(ValueError) as excinfo:
        user.email_user("my subject", "my message")

    assert str(excinfo.value) == "User has no email address."


def test_models_users_convert_valid_invitations():
    """
    The "_convert_valid_invitations" method should convert valid invitations to item accesses.
    """
    email = "test@example.com"
    item = factories.ItemFactory()
    other_item = factories.ItemFactory()
    invitation_item = factories.InvitationFactory(email=email, item=item)
    invitation_other_item = factories.InvitationFactory(email="Test@example.coM", item=other_item)
    other_email_invitation = factories.InvitationFactory(email="pre_test@example.com", item=item)

    assert item.accesses.count() == 0
    assert other_item.accesses.count() == 0

    user = factories.UserFactory(email=email)

    assert item.accesses.filter(user=user).count() == 1
    assert other_item.accesses.filter(user=user).count() == 1

    assert not models.Invitation.objects.filter(id=invitation_item.id).exists()
    assert not models.Invitation.objects.filter(id=invitation_other_item.id).exists()
    assert models.Invitation.objects.filter(id=other_email_invitation.id).exists()


def test_models_users_send_reconciliation_email():
    """The "send_reconciliation_email" method should send a templated email to the user."""
    user = factories.UserFactory(email="recipient@example.com")

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 0

    user.send_reconciliation_email(
        "my subject",
        {
            "title": "My title",
            "message": "My message",
            "link": "https://example.com/some-link/",
            "link_label": "Click here",
            "button_label": "Confirm",
        },
        "en",
    )

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 1

    # pylint: disable-next=no-member
    email = mail.outbox[0]

    assert email.to == ["recipient@example.com"]
    email_content = " ".join(email.body.split())

    assert "My message" in email_content
    assert "https://example.com/some-link/" in email_content


def test_models_users_unlocked_link_items():
    """A user loaded from the database should keep the roles granted by unlocked links."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="public", link_role="editor")
    item.set_link_password("s3cret")
    item.save()
    models.LinkTrace.objects.create(user=user, item=item, link_unlocked_at=timezone.now())

    user = models.User.objects.get(pk=user.pk)

    assert user.unlocked_link_items == {item.link_unlock_key}
    assert item.get_abilities(user)["update"] is True


def test_models_users_unlocked_link_items_password_cleared():
    """An unlocked trace on an item that lost its link password should be ignored."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach="public")
    item.set_link_password("s3cret")
    item.save()
    models.LinkTrace.objects.create(user=user, item=item, link_unlocked_at=timezone.now())
    models.Item.objects.filter(pk=item.pk).update(link_password=None)

    assert user.unlocked_link_items == set()
