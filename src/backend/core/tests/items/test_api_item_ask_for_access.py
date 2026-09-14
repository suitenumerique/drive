"""Test API for item ask for access."""

import uuid

from django.core import mail

import pytest
from lasuite.drf.models.choices import PRIVILEGED_ROLES, RoleChoices
from rest_framework.test import APIClient

from core.api.serializers import ItemAskForAccessSerializer
from core.factories import (
    ItemAskForAccessFactory,
    ItemFactory,
    UserFactory,
    UserItemAccessFactory,
)
from core.models import ItemAccess, ItemAskForAccess

pytestmark = pytest.mark.django_db


## Create


def test_api_item_ask_for_access_create_anonymous():
    """Anonymous users should not be able to create an item ask for access."""
    item = ItemFactory()

    client = APIClient()
    response = client.post(f"/api/v1.0/items/{item.id}/ask-for-access/")

    assert response.status_code == 401


def test_api_item_ask_for_access_create_invalid_item_id():
    """Invalid item ID should return a 404 error."""
    user = UserFactory()

    client = APIClient()
    client.force_login(user)
    response = client.post(f"/api/v1.0/items/{uuid.uuid4()}/ask-for-access/")

    assert response.status_code == 404


def test_api_item_ask_for_access_create_authenticated():
    """
    Authenticated users should be able to create an item ask for access.
    An email should be sent to item owners and admins to notify them.
    """
    owner_user = UserFactory(language="en-us")
    admin_user = UserFactory(language="en-us")
    item = ItemFactory(
        users=[
            (owner_user, RoleChoices.OWNER),
            (admin_user, RoleChoices.ADMIN),
        ]
    )

    user = UserFactory()

    client = APIClient()
    client.force_login(user)

    assert len(mail.outbox) == 0

    response = client.post(f"/api/v1.0/items/{item.id}/ask-for-access/")
    assert response.status_code == 201

    assert ItemAskForAccess.objects.filter(
        item=item,
        user=user,
        role=RoleChoices.READER,
    ).exists()

    # Verify emails were sent to both owner and admin
    assert len(mail.outbox) == 2

    # Check that emails were sent to the right recipients
    email_recipients = [email.to[0] for email in mail.outbox]
    assert owner_user.email in email_recipients
    assert admin_user.email in email_recipients

    # Check email content for both users
    for email in mail.outbox:
        email_content = " ".join(email.body.split())
        email_subject = " ".join(email.subject.split())

        # Check that the requesting user's name is in the email
        user_name = user.full_name or user.email
        assert user_name.lower() in email_content.lower()

        # Check that the subject mentions access request
        assert "access" in email_subject.lower()

        # Check that the item title is mentioned if it exists
        if item.title:
            assert item.title.lower() in email_subject.lower()


@pytest.mark.parametrize("role", [role for role in RoleChoices if role != RoleChoices.OWNER])
def test_api_item_ask_for_access_create_authenticated_specific_role(role):
    """
    Authenticated users should be able to create an item ask for access with a specific role.
    """
    item = ItemFactory()
    user = UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/",
        data={"role": role},
    )
    assert response.status_code == 201

    assert ItemAskForAccess.objects.filter(
        item=item,
        user=user,
        role=role,
    ).exists()


def test_api_item_ask_for_access_create_authenticated_owner_role():
    """
    Authenticated users should not be able to create an item ask for access with the owner role.
    """
    item = ItemFactory()
    user = UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/",
        data={"role": RoleChoices.OWNER},
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "role",
                "code": "invalid_choice",
                "detail": '"owner" is not a valid choice.',
            }
        ],
        "type": "validation_error",
    }


def test_api_item_ask_for_access_create_authenticated_already_has_access():
    """Authenticated users with existing access can ask for access with a different role."""
    user = UserFactory()
    item = ItemFactory(users=[(user, RoleChoices.READER)])

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/",
        data={"role": RoleChoices.EDITOR},
    )
    assert response.status_code == 201

    assert ItemAskForAccess.objects.filter(
        item=item,
        user=user,
        role=RoleChoices.EDITOR,
    ).exists()


def test_api_item_ask_for_access_create_authenticated_already_has_ask_for_access():
    """
    Authenticated users with an existing ask for access cannot ask for a new access on this item.
    """
    user = UserFactory()
    item = ItemFactory(users=[(user, RoleChoices.READER)])
    ItemAskForAccessFactory(item=item, user=user, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/",
        data={"role": RoleChoices.EDITOR},
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "already_requested",
                "detail": "You have already requested access to this item.",
            }
        ],
        "type": "validation_error",
    }


@pytest.mark.parametrize("role", PRIVILEGED_ROLES)
def test_api_item_ask_for_access_create_authenticated_already_has_privileged_access(role):
    """
    Authenticated users with privileged access (owner or admin) should not be able to
    create an item ask for access.
    """
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])

    client = APIClient()
    client.force_login(user)

    response = client.post(f"/api/v1.0/items/{item.id}/ask-for-access/")
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "already_has_privileged_access",
                "detail": "You already have privileged access to this item.",
            }
        ],
        "type": "validation_error",
    }


## List


def test_api_item_ask_for_access_list_anonymous():
    """Anonymous users should not be able to list item ask for access."""
    item = ItemFactory()
    ItemAskForAccessFactory.create_batch(3, item=item, role=RoleChoices.READER)

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/")

    assert response.status_code == 401


def test_api_item_ask_for_access_list_authenticated():
    """Authenticated unrelated users should see an empty list."""
    item = ItemFactory()
    ItemAskForAccessFactory.create_batch(3, item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(UserFactory())

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/")
    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


def test_api_item_ask_for_access_list_authenticated_own_request():
    """Authenticated users should be able to list their own item ask for access."""
    item = ItemFactory()
    ItemAskForAccessFactory.create_batch(3, item=item, role=RoleChoices.READER)

    user = UserFactory()

    item_ask_for_access = ItemAskForAccessFactory(item=item, user=user, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/")
    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": str(item_ask_for_access.id),
                "item": str(item.id),
                "user": ItemAskForAccessSerializer(instance=item_ask_for_access).data["user"],
                "role": RoleChoices.READER,
                "created_at": item_ask_for_access.created_at.isoformat().replace("+00:00", "Z"),
                "abilities": {
                    "accept": False,
                    "destroy": False,
                    "retrieve": False,
                    "set_role_to": [],
                },
            }
        ],
    }


def test_api_item_ask_for_access_list_authenticated_other_item():
    """Authenticated users should not be able to list item ask for access of other items."""
    item = ItemFactory()
    ItemAskForAccessFactory.create_batch(3, item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(UserFactory())

    other_item = ItemFactory()
    ItemAskForAccessFactory.create_batch(3, item=other_item, role=RoleChoices.READER)

    response = client.get(f"/api/v1.0/items/{other_item.id}/ask-for-access/")
    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


@pytest.mark.parametrize("role", [RoleChoices.READER, RoleChoices.EDITOR])
def test_api_item_ask_for_access_list_non_owner_or_admin(role):
    """Non owner or admin users should not be able to list other users' access requests."""
    user = UserFactory()

    item = ItemFactory(users=[(user, role)])
    ItemAskForAccessFactory.create_batch(3, item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/")
    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


@pytest.mark.parametrize("role", [RoleChoices.OWNER, RoleChoices.ADMIN])
def test_api_item_ask_for_access_list_owner_or_admin(role):
    """Owner or admin users should be able to list all item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_accesses = ItemAskForAccessFactory.create_batch(
        3, item=item, role=RoleChoices.READER
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/")
    assert response.status_code == 200

    expected_set_role_to = [RoleChoices.READER, RoleChoices.EDITOR, RoleChoices.ADMIN]
    if role == RoleChoices.OWNER:
        expected_set_role_to.append(RoleChoices.OWNER)

    assert response.json() == {
        "count": 3,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": str(item_ask_for_access.id),
                "item": str(item.id),
                "user": ItemAskForAccessSerializer(instance=item_ask_for_access).data["user"],
                "role": RoleChoices.READER,
                "created_at": item_ask_for_access.created_at.isoformat().replace("+00:00", "Z"),
                "abilities": {
                    "accept": True,
                    "destroy": True,
                    "retrieve": True,
                    "set_role_to": expected_set_role_to,
                },
            }
            for item_ask_for_access in item_ask_for_accesses
        ],
    }


## Retrieve


def test_api_item_ask_for_access_retrieve_anonymous():
    """Anonymous users should not be able to retrieve item ask for access."""
    item = ItemFactory()
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 401


def test_api_item_ask_for_access_retrieve_authenticated():
    """Authenticated unrelated users should not be able to retrieve item ask for access."""
    item = ItemFactory()
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(UserFactory())

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleChoices.READER, RoleChoices.EDITOR])
def test_api_item_ask_for_access_retrieve_authenticated_non_owner_or_admin(role):
    """Non owner or admin users should not be able to retrieve item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleChoices.OWNER, RoleChoices.ADMIN])
def test_api_item_ask_for_access_retrieve_owner_or_admin(role):
    """Owner or admin users should be able to retrieve item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 200

    expected_set_role_to = [RoleChoices.READER, RoleChoices.EDITOR, RoleChoices.ADMIN]
    if role == RoleChoices.OWNER:
        expected_set_role_to.append(RoleChoices.OWNER)

    assert response.json() == {
        "id": str(item_ask_for_access.id),
        "item": str(item.id),
        "user": ItemAskForAccessSerializer(instance=item_ask_for_access).data["user"],
        "role": RoleChoices.READER,
        "created_at": item_ask_for_access.created_at.isoformat().replace("+00:00", "Z"),
        "abilities": {
            "accept": True,
            "destroy": True,
            "retrieve": True,
            "set_role_to": expected_set_role_to,
        },
    }


## Delete


def test_api_item_ask_for_access_delete_anonymous():
    """Anonymous users should not be able to delete item ask for access."""
    item = ItemFactory()
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    response = client.delete(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 401


def test_api_item_ask_for_access_delete_authenticated():
    """Authenticated unrelated users should not be able to delete item ask for access."""
    item = ItemFactory()
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(UserFactory())

    response = client.delete(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleChoices.READER, RoleChoices.EDITOR])
def test_api_item_ask_for_access_delete_authenticated_non_owner_or_admin(role):
    """Non owner or admin users should not be able to delete item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleChoices.OWNER, RoleChoices.ADMIN])
def test_api_item_ask_for_access_delete_owner_or_admin(role):
    """Owner or admin users should be able to delete item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.delete(f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/")
    assert response.status_code == 204
    assert not ItemAskForAccess.objects.filter(id=item_ask_for_access.id).exists()


## Accept


def test_api_item_ask_for_access_accept_anonymous():
    """Anonymous users should not be able to accept item ask for access."""
    item = ItemFactory()
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/"
    )
    assert response.status_code == 401


def test_api_item_ask_for_access_accept_authenticated():
    """Authenticated unrelated users should not be able to accept item ask for access."""
    item = ItemFactory()
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(UserFactory())
    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/"
    )
    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleChoices.READER, RoleChoices.EDITOR])
def test_api_item_ask_for_access_accept_authenticated_non_owner_or_admin(role):
    """Non owner or admin users should not be able to accept item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/"
    )
    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleChoices.OWNER, RoleChoices.ADMIN])
def test_api_item_ask_for_access_accept_owner_or_admin(role):
    """Owner or admin users should be able to accept item ask for access."""
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/"
    )
    assert response.status_code == 204

    assert not ItemAskForAccess.objects.filter(id=item_ask_for_access.id).exists()
    assert ItemAccess.objects.filter(
        item=item, user=item_ask_for_access.user, role=RoleChoices.READER
    ).exists()


@pytest.mark.parametrize("role", [RoleChoices.OWNER, RoleChoices.ADMIN])
def test_api_item_ask_for_access_accept_authenticated_specific_role(role):
    """
    Owner or admin users should be able to accept item ask for access with a specific role.
    """
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/",
        data={"role": RoleChoices.EDITOR},
    )
    assert response.status_code == 204

    assert not ItemAskForAccess.objects.filter(id=item_ask_for_access.id).exists()
    assert ItemAccess.objects.filter(
        item=item, user=item_ask_for_access.user, role=RoleChoices.EDITOR
    ).exists()


@pytest.mark.parametrize("role", [RoleChoices.OWNER, RoleChoices.ADMIN])
def test_api_item_ask_for_access_accept_owner_or_admin_update_access(role):
    """
    Owner or admin users should be able to accept item ask for access and update the access.
    """
    user = UserFactory()
    item = ItemFactory(users=[(user, role)])
    item_access = UserItemAccessFactory(item=item, role=RoleChoices.READER)
    item_ask_for_access = ItemAskForAccessFactory(
        item=item, user=item_access.user, role=RoleChoices.EDITOR
    )

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/",
        data={"role": RoleChoices.EDITOR},
    )
    assert response.status_code == 204

    assert not ItemAskForAccess.objects.filter(id=item_ask_for_access.id).exists()
    item_access.refresh_from_db()
    assert item_access.role == RoleChoices.EDITOR


def test_api_item_ask_for_access_accept_admin_cannot_accept_owner_role():
    """
    Admin users should not be able to accept item ask for access with the owner role.
    """
    user = UserFactory()
    item = ItemFactory(users=[(user, RoleChoices.ADMIN)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/",
        data={"role": RoleChoices.OWNER},
    )
    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "role_too_high",
                "detail": "You cannot accept a role higher than your own.",
            }
        ],
        "type": "validation_error",
    }


def test_api_item_ask_for_access_accept_owner_can_accept_owner_role():
    """
    Owner users should be able to accept item ask for access with the owner role.
    """
    user = UserFactory()
    item = ItemFactory(users=[(user, RoleChoices.OWNER)])
    item_ask_for_access = ItemAskForAccessFactory(item=item, role=RoleChoices.READER)

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id}/ask-for-access/{item_ask_for_access.id}/accept/",
        data={"role": RoleChoices.OWNER},
    )
    assert response.status_code == 204

    assert not ItemAskForAccess.objects.filter(id=item_ask_for_access.id).exists()
