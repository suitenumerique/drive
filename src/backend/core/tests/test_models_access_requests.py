"""
Unit tests for the AccessRequest model
"""

from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.exceptions import ValidationError

import pytest

from core import factories, models
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_models_access_request_is_pending():
    """The 'is_pending' property should reflect the request status."""
    request = factories.AccessRequestFactory(status="pending")
    assert request.is_pending is True
    request.status = "accepted"
    assert request.is_pending is False


def test_models_access_request_str():
    """The string representation should describe the request."""
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    request = factories.AccessRequestFactory(item=item, requester=requester, status="pending")
    assert str(request) == f"{requester!s} requested access to {item!s} (pending)"


def test_models_access_request_unique_pending_per_item_and_requester():
    """
    A requester should not be able to create two pending requests for the same item,
    but should be able to reopen a request once the previous one is handled.
    """
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    first = factories.AccessRequestFactory(item=item, requester=requester, status="pending")

    with pytest.raises(ValidationError, match="already requested access"):
        factories.AccessRequestFactory(item=item, requester=requester, status="pending")

    # Once handled, a new pending request is allowed
    first.status = "refused"
    first.save()
    factories.AccessRequestFactory(item=item, requester=requester, status="pending")
    assert (
        models.AccessRequest.objects.filter(
            item=item, requester=requester, status="pending"
        ).count()
        == 1
    )


# get_abilities


def test_models_access_request_get_abilities_anonymous():
    """Check abilities returned for an anonymous user."""
    request = factories.AccessRequestFactory(status="pending")
    abilities = request.get_abilities(AnonymousUser())
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }


def test_models_access_request_get_abilities_outsider():
    """An authenticated user who is not related to the item has no ability."""
    user = factories.UserFactory()
    request = factories.AccessRequestFactory(status="pending")
    abilities = request.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }


def test_models_access_request_get_abilities_requester():
    """The requester can retrieve their own request but not manage it."""
    requester = factories.UserFactory()
    request = factories.AccessRequestFactory(requester=requester, status="pending")
    abilities = request.get_abilities(requester)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "partial_update": False,
        "update": False,
    }


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_models_access_request_get_abilities_privileged_member(role, via, mock_user_teams):
    """Check abilities for an item member with a privileged role on a pending request."""
    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    request = factories.AccessRequestFactory(item=item, status="pending")
    abilities = request.get_abilities(user)
    assert abilities == {
        "destroy": True,
        "retrieve": True,
        "partial_update": True,
        "update": True,
    }


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_models_access_request_get_abilities_unprivileged_member(role, via, mock_user_teams):
    """Readers and editors cannot manage access requests."""
    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    request = factories.AccessRequestFactory(item=item, status="pending")
    abilities = request.get_abilities(user)
    assert abilities == {
        "destroy": False,
        "retrieve": False,
        "partial_update": False,
        "update": False,
    }


def test_models_access_request_get_abilities_privileged_on_resolved():
    """Privileged members can no longer update a request once it is resolved."""
    manager = factories.UserFactory()
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=manager, role="owner")

    request = factories.AccessRequestFactory(item=item, status="accepted")
    abilities = request.get_abilities(manager)
    assert abilities == {
        "destroy": False,
        "retrieve": True,
        "partial_update": False,
        "update": False,
    }


# Item.get_owners and email


def test_models_item_get_owners_direct_and_ancestors():
    """Owners of an item (directly or via an ancestor) are returned."""
    root = factories.ItemFactory(type="folder")
    owner = factories.UserFactory()
    factories.UserItemAccessFactory(item=root, user=owner, role="owner")

    child = factories.ItemFactory(parent=root, type="folder")

    parents = child.get_owners()
    assert owner in parents


def test_models_item_send_access_request_email(
    settings,
):
    """The item owner is notified when someone requests access."""
    requester = factories.UserFactory(language=settings.LANGUAGE_CODE)
    owner = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=owner, role="owner")

    item.send_access_request_email(requester, "I need access", [owner], settings.LANGUAGE_CODE)

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [owner.email]
    assert item.title in " ".join(email.body.split())


def test_models_item_send_access_request_answer_email_accepted(settings):
    """The requester is notified when their request is accepted."""
    requester = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()

    item.send_access_request_answer_email(requester, True, settings.LANGUAGE_CODE)

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [requester.email]
    assert "accepted" in " ".join(email.body.split())
