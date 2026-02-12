"""
Unit tests for the Invitation model
"""

import random
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


# List


def test_api_item_invitations_list_anonymous_user():
    """Anonymous users should not be able to list invitations."""
    invitation = factories.InvitationFactory()
    response = APIClient().get(f"/api/v1.0/items/{invitation.item.id!s}/invitations/")
    assert response.status_code == 401


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_invitations_list_authenticated_privileged(
    role, via, mock_user_teams, django_assert_num_queries
):
    """
    Authenticated users should be able to list invitations for items to which they are
    related with administrator or owner privilege, including invitations issued by other users.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    invitation = factories.InvitationFactory(item=item, issuer=user)
    other_invitations = factories.InvitationFactory.create_batch(
        2, item=item, issuer=other_user
    )

    # invitations from other items should not be listed
    other_item = factories.ItemFactory()
    factories.InvitationFactory.create_batch(2, item=other_item)

    client = APIClient()
    client.force_login(user)
    with django_assert_num_queries(3):
        response = client.get(
            f"/api/v1.0/items/{item.id!s}/invitations/",
        )
    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert sorted(response.json()["results"], key=lambda x: x["created_at"]) == sorted(
        [
            {
                "id": str(i.id),
                "created_at": i.created_at.isoformat().replace("+00:00", "Z"),
                "email": str(i.email),
                "item": str(item.id),
                "role": i.role,
                "issuer": str(i.issuer.id),
                "is_expired": False,
                "abilities": {
                    "destroy": role in ["administrator", "owner"],
                    "update": role in ["administrator", "owner"],
                    "partial_update": role in ["administrator", "owner"],
                    "retrieve": True,
                },
            }
            for i in [invitation, *other_invitations]
        ],
        key=lambda x: x["created_at"],
    )


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_invitations_list_authenticated_unprivileged(
    role, via, mock_user_teams, django_assert_num_queries
):
    """
    Authenticated users should not be able to list invitations for items to which they are
    related with reader or editor role, including invitations issued by other users.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    factories.InvitationFactory(item=item, issuer=user)
    factories.InvitationFactory.create_batch(2, item=item, issuer=other_user)

    # invitations from other items should not be listed
    other_item = factories.ItemFactory()
    factories.InvitationFactory.create_batch(2, item=other_item)

    client = APIClient()
    client.force_login(user)
    with django_assert_num_queries(2):
        response = client.get(
            f"/api/v1.0/items/{item.id!s}/invitations/",
        )
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_api_item_invitations_list_expired_invitations_still_listed():
    """
    Expired invitations are still listed.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()

    item = factories.ItemFactory(users=[(user, "administrator"), (other_user, "owner")])

    expired_invitation = factories.InvitationFactory(
        item=item,
        role="reader",
        issuer=user,
    )

    client = APIClient()
    client.force_login(user)

    # mock timezone.now to accelerate validation expiration
    too_late = timezone.now() + timedelta(seconds=604800)  # 7 days
    with mock.patch("django.utils.timezone.now", return_value=too_late):
        assert expired_invitation.is_expired is True

        response = client.get(
            f"/api/v1.0/items/{item.id!s}/invitations/",
        )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert sorted(response.json()["results"], key=lambda x: x["created_at"]) == sorted(
        [
            {
                "id": str(expired_invitation.id),
                "created_at": expired_invitation.created_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "email": str(expired_invitation.email),
                "item": str(item.id),
                "role": expired_invitation.role,
                "issuer": str(expired_invitation.issuer.id),
                "is_expired": True,
                "abilities": {
                    "destroy": True,
                    "update": True,
                    "partial_update": True,
                    "retrieve": True,
                },
            },
        ],
        key=lambda x: x["created_at"],
    )


# Retrieve


def test_api_item_invitations_retrieve_anonymous_user():
    """
    Anonymous users should not be able to retrieve invitations.
    """

    invitation = factories.InvitationFactory()
    response = APIClient().get(
        f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/",
    )

    assert response.status_code == 401


def test_api_item_invitations_retrieve_unrelated_user():
    """
    Authenticated unrelated users should not be able to retrieve invitations.
    """
    user = factories.UserFactory()
    invitation = factories.InvitationFactory()

    client = APIClient()
    client.force_login(user)
    response = client.get(
        f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/",
    )

    assert response.status_code == 403


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_api_item_invitations_retrieve_item_privileged(role, via, mock_user_teams):
    """
    Authenticated users related to the item should be able to retrieve invitations
    provided they are administrators or owners of the item.
    """
    user = factories.UserFactory()
    invitation = factories.InvitationFactory()

    if via == USER:
        factories.UserItemAccessFactory(item=invitation.item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=invitation.item, team="lasuite", role=role)

    client = APIClient()
    client.force_login(user)

    response = client.get(
        f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/",
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(invitation.id),
        "created_at": invitation.created_at.isoformat().replace("+00:00", "Z"),
        "email": invitation.email,
        "item": str(invitation.item.id),
        "role": str(invitation.role),
        "issuer": str(invitation.issuer.id),
        "is_expired": False,
        "abilities": {
            "destroy": True,
            "update": True,
            "partial_update": True,
            "retrieve": True,
        },
    }


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_invitations_retrieve_item_unprivileged(role, via, mock_user_teams):
    """
    Authenticated users related to the item should not be able to retrieve invitations
    if they are simply reader or editor of the item.
    """
    user = factories.UserFactory()
    invitation = factories.InvitationFactory()

    if via == USER:
        factories.UserItemAccessFactory(item=invitation.item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=invitation.item, team="lasuite", role=role)

    client = APIClient()
    client.force_login(user)

    response = client.get(
        f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/",
    )

    assert response.status_code == 403
    assert response.content


# Create


def test_api_item_invitations_create_anonymous():
    """Anonymous users should not be able to create invitations."""
    item = factories.ItemFactory()
    invitation_values = {
        "email": "guest@example.com",
        "role": random.choice(models.RoleChoices.values),
    }

    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 401
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
    }


def test_api_item_invitations_create_authenticated_outsider():
    """Users outside of item should not be permitted to invite to item."""
    user = factories.UserFactory()
    item = factories.ItemFactory()
    invitation_values = {
        "email": "guest@example.com",
        "role": random.choice(models.RoleChoices.values),
    }

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 403


@override_settings(EMAIL_BRAND_NAME="My brand name", EMAIL_LOGO_IMG="my-img.jpg")
@pytest.mark.parametrize(
    "inviting,invited,response_code",
    (
        ["reader", "reader", 403],
        ["reader", "editor", 403],
        ["reader", "administrator", 403],
        ["reader", "owner", 403],
        ["editor", "reader", 403],
        ["editor", "editor", 403],
        ["editor", "administrator", 403],
        ["editor", "owner", 403],
        ["administrator", "reader", 201],
        ["administrator", "editor", 201],
        ["administrator", "administrator", 201],
        ["administrator", "owner", 400],
        ["owner", "reader", 201],
        ["owner", "editor", 201],
        ["owner", "administrator", 201],
        ["owner", "owner", 201],
    ),
)
@pytest.mark.parametrize("via", VIA)
def test_api_item_invitations_create_privileged_members(
    via, inviting, invited, response_code, mock_user_teams
):
    """
    Only owners and administrators should be able to invite new users.
    Only owners can invite owners.
    """
    user = factories.UserFactory(language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=inviting)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=inviting)

    invitation_values = {
        "email": "guest@example.com",
        "role": invited,
    }

    assert len(mail.outbox) == 0

    client = APIClient()
    client.force_login(user)
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == response_code

    if response_code == 201:
        assert models.Invitation.objects.count() == 1

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["guest@example.com"]
        email_content = " ".join(email.body.split())
        assert f"{user.full_name} shared an item with you!" in email_content
        assert (
            f"{user.full_name} ({user.email}) invited you with the role &quot;{invited}&quot; "
            f"on the following item: {item.title}"
        ) in email_content
        assert "My brand name" in email_content
        assert "my-img.jpg" in email_content
    else:
        assert models.Invitation.objects.exists() is False

    if response_code == 400:
        assert response.json() == {
            "errors": [
                {
                    "attr": "role",
                    "code": "invitation_role_owner_limited_to_owners",
                    "detail": "Only owners of a item can invite other users as owners.",
                },
            ],
            "type": "validation_error",
        }


def test_api_item_invitations_create_email_full_name_empty():
    """
    If the full name of the user is empty, it will display the email address.
    """
    user = factories.UserFactory(full_name="", language=settings.LANGUAGE_CODE)
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=user, role="owner")

    invitation_values = {
        "email": "guest@example.com",
        "role": "reader",
    }

    assert len(mail.outbox) == 0

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
        headers={"Content-Language": "not-supported"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "guest@example.com"
    assert models.Invitation.objects.count() == 1
    assert len(mail.outbox) == 1

    email = mail.outbox[0]

    assert email.to == ["guest@example.com"]

    email_content = " ".join(email.body.split())
    assert f"{user.email} shared an item with you!" in email_content
    assert (
        f"{user.email.capitalize()} invited you with the role &quot;reader&quot; on the "
        f"following item: {item.title}" in email_content
    )


def test_api_item_invitations_create_issuer_and_item_override():
    """It should not be possible to set the "item" and "issuer" fields."""
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    other_item = factories.ItemFactory(users=[(user, "owner")])
    invitation_values = {
        "item": str(other_item.id),
        "issuer": str(factories.UserFactory().id),
        "email": "guest@example.com",
        "role": random.choice(models.RoleChoices.values),
    }

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 201
    # item and issuer automatically set
    assert response.json()["item"] == str(item.id)
    assert response.json()["issuer"] == str(user.id)


def test_api_item_invitations_create_cannot_duplicate_invitation():
    """An email should not be invited multiple times to the same item."""
    existing_invitation = factories.InvitationFactory()
    item = existing_invitation.item

    # Grant privileged role on the item to the user
    user = factories.UserFactory()
    models.ItemAccess.objects.create(item=item, user=user, role="administrator")

    # Create a new invitation to the same item with the exact same email address
    invitation_values = {
        "email": existing_invitation.email,
        "role": random.choice(["administrator", "editor", "reader"]),
    }

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "errors": [
            {
                "attr": "__all__",
                "code": "unique_together",
                "detail": "Item invitation with this Email address and Item already exists.",
            },
        ],
        "type": "validation_error",
    }


def test_api_item_invitations_create_cannot_invite_existing_users():
    """
    It should not be possible to invite already existing users.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    existing_user = factories.UserFactory()

    # Build an invitation to the email of an exising identity in the db
    invitation_values = {
        "email": existing_user.email,
        "role": random.choice(models.RoleChoices.values),
    }

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "code": "invitation_email_already_registered",
                "detail": "This email is already associated to a registered user.",
                "attr": "email",
            }
        ],
    }


def test_api_item_invitations_create_cannot_invite_existing_users_case_insensitive():
    """
    It should not be possible to invite already existing users, even with different email case.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])
    _existing_user = factories.UserFactory(email="john.doe@example.com")

    # Build an invitation to the email of an existing identity with different case
    invitation_values = {
        "email": "JOHN.DOE@EXAMPLE.COM",
        "role": random.choice(models.RoleChoices.values),
    }

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "validation_error",
        "errors": [
            {
                "code": "invitation_email_already_registered",
                "detail": "This email is already associated to a registered user.",
                "attr": "email",
            }
        ],
    }


# Update


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_api_item_invitations_update_authenticated_privileged_any_field_except_role(
    role, via, mock_user_teams
):
    """
    Authenticated user can update invitations if they are administrator or owner of the item.
    """
    user = factories.UserFactory()
    invitation = factories.InvitationFactory()

    if via == USER:
        factories.UserItemAccessFactory(item=invitation.item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=invitation.item, team="lasuite", role=role)

    old_invitation_values = serializers.InvitationSerializer(instance=invitation).data
    new_invitation_values = serializers.InvitationSerializer(
        instance=factories.InvitationFactory()
    ).data
    # The update of a role is tested in the next test
    del new_invitation_values["role"]

    client = APIClient()
    client.force_login(user)

    url = f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/"
    response = client.put(url, new_invitation_values, format="json")

    assert response.status_code == 200

    invitation.refresh_from_db()
    invitation_values = serializers.InvitationSerializer(instance=invitation).data

    for key, value in invitation_values.items():
        if key == "email":
            assert value == new_invitation_values[key]
        elif key == "updated_at":
            assert value > old_invitation_values[key]
        else:
            assert value == old_invitation_values[key]


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role_set", models.RoleChoices.values)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_api_item_invitations_update_authenticated_privileged_role(
    role, role_set, via, mock_user_teams
):
    """
    Authenticated user can update invitations if they are administrator or owner of the item,
    but only owners can set the invitation role to the "owner" role.
    """
    user = factories.UserFactory()
    invitation = factories.InvitationFactory()
    old_role = invitation.role

    if via == USER:
        factories.UserItemAccessFactory(item=invitation.item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=invitation.item, team="lasuite", role=role)

    new_invitation_values = serializers.InvitationSerializer(instance=invitation).data
    new_invitation_values["role"] = role_set

    client = APIClient()
    client.force_login(user)

    url = f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/"
    response = client.put(url, new_invitation_values, format="json")

    invitation.refresh_from_db()

    if role_set == "owner" and role != "owner":
        assert response.status_code == 400
        assert invitation.role == old_role
        assert response.json() == {
            "type": "validation_error",
            "errors": [
                {
                    "code": "invitation_role_owner_limited_to_owners",
                    "detail": "Only owners of a item can invite other users as owners.",
                    "attr": "role",
                }
            ],
        }
    else:
        assert response.status_code == 200
        assert invitation.role == role_set


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["reader", "editor"])
def test_api_item_invitations_update_authenticated_unprivileged(
    role, via, mock_user_teams
):
    """
    Authenticated user should not be allowed to update invitations if they are
    simple reader or editor of the item.
    """
    user = factories.UserFactory()
    invitation = factories.InvitationFactory()

    if via == USER:
        factories.UserItemAccessFactory(item=invitation.item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=invitation.item, team="lasuite", role=role)

    old_invitation_values = serializers.InvitationSerializer(instance=invitation).data
    new_invitation_values = serializers.InvitationSerializer(
        instance=factories.InvitationFactory()
    ).data

    client = APIClient()
    client.force_login(user)

    url = f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/"
    response = client.put(url, new_invitation_values, format="json")

    assert response.status_code == 403

    invitation.refresh_from_db()
    invitation_values = serializers.InvitationSerializer(instance=invitation).data

    for key, value in invitation_values.items():
        assert value == old_invitation_values[key]


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["administrator", "owner"])
def test_api_item_invitations_patch(via, role, mock_user_teams):
    """Partially updating an invitation should be allowed."""
    user = factories.UserFactory()
    invitation = factories.InvitationFactory(role="editor")

    if via == USER:
        factories.UserItemAccessFactory(item=invitation.item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=invitation.item, team="lasuite", role=role)

    client = APIClient()
    client.force_login(user)

    response = client.patch(
        f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/",
        {"role": "reader"},
        format="json",
    )
    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.role == "reader"


# Delete


def test_api_item_invitations_delete_anonymous():
    """Anonymous user should not be able to delete invitations."""
    invitation = factories.InvitationFactory()

    response = APIClient().delete(
        f"/api/v1.0/items/{invitation.item.id!s}/invitations/{invitation.id!s}/",
    )
    assert response.status_code == 401


def test_api_item_invitations_delete_authenticated_outsider():
    """Members unrelated to a item should not be allowed to cancel invitations."""
    user = factories.UserFactory()

    item = factories.ItemFactory()
    invitation = factories.InvitationFactory(item=item)

    client = APIClient()
    client.force_login(user)

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/invitations/{invitation.id!s}/",
    )
    assert response.status_code == 403


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize("role", ["owner", "administrator"])
def test_api_item_invitations_delete_privileged_members(role, via, mock_user_teams):
    """Privileged member should be able to cancel invitation."""
    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    invitation = factories.InvitationFactory(item=item)

    client = APIClient()
    client.force_login(user)

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/invitations/{invitation.id!s}/",
    )
    assert response.status_code == 204


@pytest.mark.parametrize("role", ["reader", "editor"])
@pytest.mark.parametrize("via", VIA)
def test_api_item_invitations_delete_readers_or_editors(via, role, mock_user_teams):
    """Readers or editors should not be able to cancel invitation."""
    user = factories.UserFactory()
    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    invitation = factories.InvitationFactory(item=item)

    client = APIClient()
    client.force_login(user)

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/invitations/{invitation.id!s}/",
    )
    assert response.status_code == 403
    assert response.json() == {
        "type": "client_error",
        "errors": [
            {
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
                "attr": None,
            }
        ],
    }


def test_api_item_invitations_create_lower_email():
    """
    No matter the case, the email should be converted to lowercase.
    """
    user = factories.UserFactory()
    item = factories.ItemFactory(users=[(user, "owner")])

    # Build an invitation to the email of an existing identity in the db
    invitation_values = {
        "email": "GuEst@example.com",
        "role": random.choice(models.RoleChoices.values),
    }

    client = APIClient()
    client.force_login(user)

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/invitations/",
        invitation_values,
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["email"] == "guest@example.com"
