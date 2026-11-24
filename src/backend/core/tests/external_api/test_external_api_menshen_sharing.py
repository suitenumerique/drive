"""
Tests for sharing items through the external API with an exchanged token.

A service shares an item on behalf of its user the way that user would: it looks for
the person to share with, then gives them an access, or invites their email when they
have no account yet. Each step is served by a resource of its own, opened by its own
EXTERNAL_API entry and its own scopes.
"""

from django.core import mail

import pytest

from core import factories, models
from core.tests.utils.menshen import ALL_SCOPES, MENSHEN_REQUIRED_SCOPES, menshen_client
from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument

EXTERNAL_API = {
    "items": {"enabled": True, "actions": ["list"]},
    "item_access": {
        "enabled": True,
        "actions": ["list", "create", "partial_update", "destroy"],
    },
    "item_invitation": {
        "enabled": True,
        "actions": ["list", "create", "partial_update", "destroy"],
    },
    "users": {"enabled": True, "actions": ["list", "get_me"]},
}

# Requests that need no existing object, and the scope each of them requires.
REQUESTS = [
    ("GET users/", "drive:user:list"),
    ("GET users/me/", "drive:user:me"),
    ("GET items/{item_id}/accesses/", "drive:item-access:list"),
    ("POST items/{item_id}/accesses/", "drive:item-access:create"),
    ("GET items/{item_id}/invitations/", "drive:item-invitation:list"),
    ("POST items/{item_id}/invitations/", "drive:item-invitation:create"),
]


@pytest.fixture(name="menshen_sharing_conf")
def menshen_sharing_conf_fixture(menshen_backend_conf):
    """Open the resources items are shared through, most of them closed by default."""
    menshen_backend_conf.EXTERNAL_API = EXTERNAL_API
    reload_urls()

    return menshen_backend_conf


def create_item(user, role=models.RoleChoices.OWNER):
    """Create an item the user has the given role on."""
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(item=item, user=user, role=role)

    return item


def send(client, endpoint, item):
    """Send one of REQUESTS. A create carries no data: let through, it answers a 400."""
    method, path = endpoint.split()

    return client.generic(method, f"/external_api/v1.0/{path.format(item_id=item.id)}")


# What opens a request


@pytest.mark.parametrize("endpoint,scope", REQUESTS)
def test_api_sharing_menshen_with_the_required_scope(
    menshen_sharing_conf, httpx2_mock, user_specific_sub, endpoint, scope
):
    """A token carrying nothing but the required scope should be let through."""
    item = create_item(user_specific_sub)

    response = send(menshen_client(httpx2_mock, scope), endpoint, item)

    assert response.status_code == (200 if endpoint.startswith("GET") else 400)


@pytest.mark.parametrize("endpoint,scope", REQUESTS)
def test_api_sharing_menshen_without_the_required_scope(
    menshen_sharing_conf, httpx2_mock, user_specific_sub, endpoint, scope
):
    """No other scope should stand in for the required one, whatever the resource."""
    item = create_item(user_specific_sub)
    scopes = " ".join(other for other in ALL_SCOPES.split() if other != scope)

    response = send(menshen_client(httpx2_mock, scopes), endpoint, item)

    assert response.status_code == 403


@pytest.mark.parametrize("endpoint,scope", REQUESTS)
def test_api_sharing_menshen_resource_absent_from_the_mapping(
    menshen_sharing_conf, httpx2_mock, user_specific_sub, endpoint, scope
):
    """A mapping that covers items only should open nothing else."""
    menshen_sharing_conf.MENSHEN_REQUIRED_SCOPES = {"items": MENSHEN_REQUIRED_SCOPES["items"]}
    item = create_item(user_specific_sub)

    response = send(menshen_client(httpx2_mock, ALL_SCOPES), endpoint, item)

    assert response.status_code == 403


@pytest.mark.parametrize("endpoint,scope", REQUESTS)
def test_api_sharing_menshen_action_not_opened(
    menshen_sharing_conf, httpx2_mock, user_specific_sub, endpoint, scope
):
    """An action EXTERNAL_API does not open should stay out of reach, scope or not."""
    menshen_sharing_conf.EXTERNAL_API = {
        resource: {"enabled": True, "actions": []} for resource in EXTERNAL_API
    }
    item = create_item(user_specific_sub)

    response = send(menshen_client(httpx2_mock, ALL_SCOPES), endpoint, item)

    assert response.status_code == 403


# Users


def test_api_users_me_menshen(menshen_sharing_conf, httpx2_mock, user_specific_sub):
    """An exchanged token should speak for the user it was issued for."""
    response = menshen_client(httpx2_mock, "drive:user:me").get("/external_api/v1.0/users/me/")

    assert response.status_code == 200
    assert response.json()["id"] == str(user_specific_sub.id)


# Accesses


def test_api_item_accesses_menshen_share_with_a_user(
    menshen_sharing_conf, httpx2_mock, user_specific_sub
):
    """An item should be shared with the user found from their email."""
    item = create_item(user_specific_sub)
    other_user = factories.UserFactory(email="colleague@example.com")
    client = menshen_client(httpx2_mock, "drive:user:list drive:item-access:create")

    response = client.get("/external_api/v1.0/users/", {"q": "colleague@example.com"})

    assert response.status_code == 200
    assert [user["id"] for user in response.json()] == [str(other_user.id)]

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        {"user_id": str(other_user.id), "role": models.RoleChoices.OWNER},
        format="json",
    )

    assert response.status_code == 201
    assert item.accesses.get(user=other_user).role == models.RoleChoices.OWNER
    assert [message.to for message in mail.outbox] == [["colleague@example.com"]]


@pytest.mark.parametrize("role", [models.RoleChoices.READER, models.RoleChoices.EDITOR])
def test_api_item_accesses_menshen_create_without_a_privileged_role(
    menshen_sharing_conf, httpx2_mock, user_specific_sub, role
):
    """The scope should not stand in for the user's own right to share the item."""
    item = create_item(user_specific_sub, role=role)
    other_user = factories.UserFactory()

    response = menshen_client(httpx2_mock, "drive:item-access:create").post(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        {"user_id": str(other_user.id), "role": models.RoleChoices.READER},
        format="json",
    )

    assert response.status_code == 403
    assert not item.accesses.filter(user=other_user).exists()


def test_api_item_accesses_menshen_update_and_delete(
    menshen_sharing_conf, httpx2_mock, user_specific_sub
):
    """Actions on an existing access should be reachable with their scopes."""
    item = create_item(user_specific_sub)
    access = factories.UserItemAccessFactory(item=item, role=models.RoleChoices.READER)
    url = f"/external_api/v1.0/items/{item.id!s}/accesses/{access.id!s}/"
    client = menshen_client(
        httpx2_mock, "drive:item-access:update-partial drive:item-access:delete"
    )

    response = client.patch(url, {"role": models.RoleChoices.EDITOR}, format="json")

    assert response.status_code == 200
    access.refresh_from_db()
    assert access.role == models.RoleChoices.EDITOR

    assert client.delete(url).status_code == 204
    assert not models.ItemAccess.objects.filter(pk=access.pk).exists()


# Invitations


def test_api_item_invitations_menshen_share_with_an_unknown_email(
    menshen_sharing_conf, httpx2_mock, user_specific_sub
):
    """An email that matches no user should be invited."""
    item = create_item(user_specific_sub)
    client = menshen_client(httpx2_mock, "drive:user:list drive:item-invitation:create")

    response = client.get("/external_api/v1.0/users/", {"q": "colleague@example.com"})

    assert response.status_code == 200
    assert response.json() == []

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/invitations/",
        {"email": "colleague@example.com", "role": models.RoleChoices.OWNER},
        format="json",
    )

    assert response.status_code == 201
    invitation = item.invitations.get(email="colleague@example.com")
    assert invitation.role == models.RoleChoices.OWNER
    assert invitation.issuer == user_specific_sub
    assert [message.to for message in mail.outbox] == [["colleague@example.com"]]


@pytest.mark.parametrize("role", [models.RoleChoices.READER, models.RoleChoices.EDITOR])
def test_api_item_invitations_menshen_create_without_a_privileged_role(
    menshen_sharing_conf, httpx2_mock, user_specific_sub, role
):
    """The scope should not stand in for the user's own right to share the item."""
    item = create_item(user_specific_sub, role=role)

    response = menshen_client(httpx2_mock, "drive:item-invitation:create").post(
        f"/external_api/v1.0/items/{item.id!s}/invitations/",
        {"email": "colleague@example.com", "role": models.RoleChoices.READER},
        format="json",
    )

    assert response.status_code == 403
    assert not item.invitations.exists()


def test_api_item_invitations_menshen_update_and_delete(
    menshen_sharing_conf, httpx2_mock, user_specific_sub
):
    """Actions on an existing invitation should be reachable with their scopes."""
    item = create_item(user_specific_sub)
    invitation = factories.InvitationFactory(
        item=item, issuer=user_specific_sub, role=models.RoleChoices.READER
    )
    url = f"/external_api/v1.0/items/{item.id!s}/invitations/{invitation.id!s}/"
    client = menshen_client(
        httpx2_mock, "drive:item-invitation:update-partial drive:item-invitation:delete"
    )

    response = client.patch(url, {"role": models.RoleChoices.EDITOR}, format="json")

    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.role == models.RoleChoices.EDITOR

    assert client.delete(url).status_code == 204
    assert not models.Invitation.objects.filter(pk=invitation.pk).exists()
