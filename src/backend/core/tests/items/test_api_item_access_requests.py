"""
Unit tests for access requests on items.
"""
# pylint: disable=too-many-arguments,too-many-positional-arguments

from django.core import mail

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


# List


def test_api_item_access_requests_list_anonymous_user():
    """Anonymous users should not be able to list access requests."""
    access_request = factories.AccessRequestFactory()
    response = APIClient().get(f"/api/v1.0/items/{access_request.item.id!s}/access-requests/")
    assert response.status_code == 401


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_access_requests_list_authenticated_privileged(role, via, mock_user_teams):
    """
    Authenticated users should be able to list access requests on items to which they are
    related with administrator or owner privilege.
    """
    user = factories.UserFactory()
    owner = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    request_owner = factories.AccessRequestFactory(item=item, requester=owner, status="pending")
    request_other = factories.AccessRequestFactory.create_batch(2, item=item, status="pending")

    # access requests from other items should not be listed
    other_item = factories.ItemFactory()
    factories.AccessRequestFactory.create_batch(2, item=other_item, status="pending")

    client = APIClient()
    client.force_login(user)
    response = client.get(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert sorted(response.json()["results"], key=lambda x: x["created_at"]) == sorted(
        [
            {
                "id": str(i.id),
                "created_at": i.created_at.isoformat().replace("+00:00", "Z"),
                "item": str(item.id),
                "status": str(i.status),
                "message": i.message,
                "requester": serializers.UserSerializer(i.requester).data,
                "abilities": {
                    "retrieve": True,
                    "update": True,
                    "partial_update": True,
                    "destroy": True,
                },
            }
            for i in [request_owner, *request_other]
        ],
        key=lambda x: x["created_at"],
    )


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_access_requests_list_authenticated_unprivileged(role, via, mock_user_teams):
    """
    Authenticated users related to the item with a reader or editor role should not be able
    to list access requests.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    factories.AccessRequestFactory.create_batch(2, item=item, status="pending")

    client = APIClient()
    client.force_login(user)
    response = client.get(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
    )
    assert response.status_code == 403


# Create


def test_api_item_access_requests_create_anonymous():
    """Anonymous users should not be able to create an access request."""
    item = factories.ItemFactory()
    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
        {"message": "Hello"},
        format="json",
    )
    assert response.status_code == 401


def test_api_item_access_requests_create_authenticated_outsider(settings):
    """
    Authenticated users without access to the item should be able to request access.
    An email is sent to the item owners.
    """
    requester = factories.UserFactory(language=settings.LANGUAGE_CODE)
    owner = factories.UserFactory(language=settings.LANGUAGE_CODE)
    other_owner = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=owner, role="owner")
    factories.UserItemAccessFactory(item=item, user=other_owner, role="owner")

    assert len(mail.outbox) == 0

    client = APIClient()
    client.force_login(requester)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
        {"message": "I need access to this folder"},
        format="json",
    )

    assert response.status_code == 201
    access_request = models.AccessRequest.objects.get()
    assert access_request.requester == requester
    assert access_request.item == item
    assert access_request.status == "pending"
    assert access_request.message == "I need access to this folder"

    assert response.json()["item"] == str(item.id)
    assert response.json()["requester"]["id"] == str(requester.id)
    assert response.json()["status"] == "pending"
    assert response.json()["message"] == "I need access to this folder"

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert sorted(email.to) == sorted([owner.email, other_owner.email])
    email_content = " ".join(email.body.split())
    assert "is asking for access" in email_content
    assert item.title in email_content


def test_api_item_access_requests_create_message_optional():
    """A request without a message should be accepted."""
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    owner = factories.UserFactory()
    factories.UserItemAccessFactory(item=item, user=owner, role="owner")

    client = APIClient()
    client.force_login(requester)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
        {},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["message"] == ""


def test_api_item_access_requests_create_duplicate_pending():
    """A user cannot create two pending requests for the same item."""
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    factories.AccessRequestFactory(item=item, requester=requester, status="pending")

    client = APIClient()
    client.force_login(requester)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
        {"message": "again"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "access_request_already_pending"
    assert models.AccessRequest.objects.count() == 1


@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_access_requests_create_user_already_has_access(role):
    """A user who already has privileged access cannot request access."""
    user = factories.UserFactory()
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=user, role=role)

    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/access-requests/",
        {"message": "I need access"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "access_request_already_has_access"
    assert models.AccessRequest.objects.count() == 0


# Update (accept / refuse)


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_access_requests_accept(role, via, mock_user_teams, settings):
    """
    An owner or administrator can accept a pending request, which grants READER access
    to the requester and notifies them by email.
    """
    manager = factories.UserFactory(language=settings.LANGUAGE_CODE)
    requester = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=manager, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access_request = factories.AccessRequestFactory(
        item=item, requester=requester, status="pending"
    )

    assert len(mail.outbox) == 0

    client = APIClient()
    client.force_login(manager)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/access-requests/{access_request.id!s}/",
        {"status": "accepted"},
        format="json",
    )

    assert response.status_code == 200
    access_request.refresh_from_db()
    assert access_request.status == "accepted"
    item_access = models.ItemAccess.objects.get(item=item, user=requester)
    assert item_access.role == "reader"

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [requester.email]
    assert "has been accepted" in " ".join(email.body.split())


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_access_requests_refuse(role, via, mock_user_teams, settings):
    """
    An owner or administrator can refuse a pending request. No access is granted and the
    requester is notified by email.
    """
    manager = factories.UserFactory(language=settings.LANGUAGE_CODE)
    requester = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=manager, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access_request = factories.AccessRequestFactory(
        item=item, requester=requester, status="pending"
    )

    assert len(mail.outbox) == 0

    client = APIClient()
    client.force_login(manager)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/access-requests/{access_request.id!s}/",
        {"status": "refused"},
        format="json",
    )

    assert response.status_code == 200
    access_request.refresh_from_db()
    assert access_request.status == "refused"
    assert not models.ItemAccess.objects.filter(item=item, user=requester).exists()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [requester.email]
    assert "declined" in " ".join(email.body.split())


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_access_requests_update_unprivileged(role, via, mock_user_teams):
    """Readers and editors should not be able to accept or refuse access requests."""
    user = factories.UserFactory()
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access_request = factories.AccessRequestFactory(
        item=item, requester=requester, status="pending"
    )

    client = APIClient()
    client.force_login(user)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/access-requests/{access_request.id!s}/",
        {"status": "accepted"},
        format="json",
    )
    assert response.status_code == 403
    access_request.refresh_from_db()
    assert access_request.status == "pending"


def test_api_item_access_requests_update_invalid_status():
    """An invalid status should be rejected."""
    manager = factories.UserFactory()
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=manager, role="owner")

    access_request = factories.AccessRequestFactory(
        item=item, requester=requester, status="pending"
    )

    client = APIClient()
    client.force_login(manager)
    response = client.patch(
        f"/api/v1.0/items/{item.id!s}/access-requests/{access_request.id!s}/",
        {"status": "not-a-status"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "invalid_access_request_status"
    access_request.refresh_from_db()
    assert access_request.status == "pending"


# Delete


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_access_requests_delete_privileged(role, via, mock_user_teams):
    """Owners and administrators should be able to delete a pending access request."""
    manager = factories.UserFactory()
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=manager, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access_request = factories.AccessRequestFactory(
        item=item, requester=requester, status="pending"
    )

    other_item_request = factories.AccessRequestFactory(status="pending")

    client = APIClient()
    client.force_login(manager)
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/access-requests/{access_request.id!s}/",
    )
    assert response.status_code == 204
    assert not models.AccessRequest.objects.filter(pk=access_request.pk).exists()
    # requests on other items are not deleted
    assert models.AccessRequest.objects.filter(pk=other_item_request.pk).exists()


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_access_requests_delete_unprivileged(role, via, mock_user_teams):
    """Readers and editors should not be able to delete access requests."""
    user = factories.UserFactory()
    requester = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access_request = factories.AccessRequestFactory(
        item=item, requester=requester, status="pending"
    )

    client = APIClient()
    client.force_login(user)
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/access-requests/{access_request.id!s}/",
    )
    assert response.status_code == 403
    assert models.AccessRequest.objects.filter(pk=access_request.pk).exists()
