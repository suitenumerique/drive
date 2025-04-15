"""
Unit tests for the Invitation model
"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core import exceptions
from django.utils import timezone

import pytest
from faker import Faker
from freezegun import freeze_time

from core import factories, models
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


fake = Faker()


def test_models_invitations_email_no_empty_mail():
    """The "email" field should not be empty."""
    with pytest.raises(exceptions.ValidationError, match="This field cannot be blank"):
        factories.InvitationFactory(email="")


def test_models_invitations_email_no_null_mail():
    """The "email" field is required."""
    with pytest.raises(exceptions.ValidationError, match="This field cannot be null"):
        factories.InvitationFactory(email=None)


def test_models_invitations_item_required():
    """The "item" field is required."""
    with pytest.raises(exceptions.ValidationError, match="This field cannot be null"):
        factories.InvitationFactory(item=None)


def test_models_invitations_item_should_be_item_instance():
    """The "item" field should be a item instance."""
    with pytest.raises(
        ValueError,
        match='Cannot assign "\'ee\'": "Invitation.item" must be a "Item" instance.',
    ):
        factories.InvitationFactory(item="ee")


def test_models_invitations_role_required():
    """The "role" field is required."""
    with pytest.raises(exceptions.ValidationError, match="This field cannot be blank"):
        factories.InvitationFactory(role="")


def test_models_invitations_role_among_choices():
    """The "role" field should be a valid choice."""
    with pytest.raises(
        exceptions.ValidationError, match="Value 'boss' is not a valid choice"
    ):
        factories.InvitationFactory(role="boss")


def test_models_invitations_is_expired():
    """
    The 'is_expired' property should return False until validity duration
    is exceeded and True afterwards.
    """
    expired_invitation = factories.InvitationFactory()
    assert expired_invitation.is_expired is False

    not_late = timezone.now() + timedelta(seconds=604799)
    with mock.patch("django.utils.timezone.now", return_value=not_late):
        assert expired_invitation.is_expired is False

    too_late = timezone.now() + timedelta(seconds=604800)  # 7 days
    with mock.patch("django.utils.timezone.now", return_value=too_late):
        assert expired_invitation.is_expired is True


def test_models_invitationd_new_userd_convert_invitations_to_accesses():
    """
    Upon creating a new user, invitations linked to the email
    should be converted to accesses and then deleted.
    """
    # Two invitations to the same mail but to different items
    invitation_to_item1 = factories.InvitationFactory()
    invitation_to_item2 = factories.InvitationFactory(email=invitation_to_item1.email)

    other_invitation = factories.InvitationFactory(
        item=invitation_to_item2.item
    )  # another person invited to item2

    new_user = factories.UserFactory(email=invitation_to_item1.email)

    # The invitation regarding
    assert models.ItemAccess.objects.filter(
        item=invitation_to_item1.item, user=new_user
    ).exists()
    assert models.ItemAccess.objects.filter(
        item=invitation_to_item2.item, user=new_user
    ).exists()
    assert not models.Invitation.objects.filter(
        item=invitation_to_item1.item, email=invitation_to_item1.email
    ).exists()  # invitation "consumed"
    assert not models.Invitation.objects.filter(
        item=invitation_to_item2.item, email=invitation_to_item2.email
    ).exists()  # invitation "consumed"
    assert models.Invitation.objects.filter(
        item=invitation_to_item2.item, email=other_invitation.email
    ).exists()  # the other invitation remains


def test_models_invitationd_new_user_filter_expired_invitations():
    """
    Upon creating a new identity, valid invitations should be converted into accesses
    and expired invitations should remain unchanged.
    """
    item = factories.ItemFactory()
    with freeze_time("2020-01-01"):
        expired_invitation = factories.InvitationFactory(item=item)
    user_email = expired_invitation.email
    valid_invitation = factories.InvitationFactory(email=user_email)

    new_user = factories.UserFactory(email=user_email)

    # valid invitation should have granted access to the related item
    assert models.ItemAccess.objects.filter(
        item=valid_invitation.item, user=new_user
    ).exists()
    assert not models.Invitation.objects.filter(
        item=valid_invitation.item, email=user_email
    ).exists()

    # expired invitation should not have been consumed
    assert not models.ItemAccess.objects.filter(
        item=expired_invitation.item, user=new_user
    ).exists()
    assert models.Invitation.objects.filter(
        item=expired_invitation.item, email=user_email
    ).exists()


@pytest.mark.parametrize("num_invitations, num_queries", [(0, 21), (1, 25), (20, 25)])
def test_models_invitations_new_userd_user_creation_constant_num_queries(
    django_assert_num_queries, num_invitations, num_queries
):
    """
    The number of queries executed during user creation should not be proportional
    to the number of invitations being processed.
    """
    user_email = fake.email()

    if num_invitations != 0:
        factories.InvitationFactory.create_batch(num_invitations, email=user_email)

    # with no invitation, we skip an "if", resulting in 8 requests
    # otherwise, we should have 11 queries with any number of invitations
    with django_assert_num_queries(num_queries):
        models.User.objects.create(email=user_email, password="!")


# get_abilities


def test_models_item_invitations_get_abilities_anonymous():
    """Check abilities returned for an anonymous user."""
    access = factories.InvitationFactory()
    abilities = access.get_abilities(AnonymousUser())
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }


def test_models_item_invitations_get_abilities_authenticated():
    """Check abilities returned for an authenticated user."""
    access = factories.InvitationFactory()
    user = factories.UserFactory()
    abilities = access.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_models_item_invitations_get_abilities_privileged_member(
    role, via, mock_user_teams
):
    """Check abilities for a item member with a privileged role."""

    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    factories.UserItemAccessFactory(item=item)  # another one

    invitation = factories.InvitationFactory(item=item)
    abilities = invitation.get_abilities(user)

    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "partial_update": True,
        "update": True,
    }


@pytest.mark.parametrize("via", VIA)
def test_models_item_invitations_get_abilities_reader(via, mock_user_teams):
    """Check abilities for a item reader with 'reader' role."""

    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role="reader")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role="reader")

    invitation = factories.InvitationFactory(item=item)
    abilities = invitation.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }


@pytest.mark.parametrize("via", VIA)
def test_models_item_invitations_get_abilities_editor(via, mock_user_teams):
    """Check abilities for a item editor with 'editor' role."""

    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role="editor")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role="editor")

    invitation = factories.InvitationFactory(item=item)
    abilities = invitation.get_abilities(user)

    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }
