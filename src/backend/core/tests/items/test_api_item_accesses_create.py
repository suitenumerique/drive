"""
Test item accesses API endpoints for users in drive's core app.
"""

import random

from django.core import mail

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_api_item_accesses_create_anonymous():
    """Anonymous users should not be allowed to create item accesses."""
    item = factories.ItemFactory()

    other_user = factories.UserFactory()
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0
    response = APIClient().post(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        {
            "user_id": str(other_user.id),
            "item": str(item.id),
            "role": random.choice(models.RoleChoices.values),
        },
        format="json",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0


def test_api_item_accesses_create_authenticated_unrelated():
    """
    Authenticated users should not be allowed to create item accesses for a item to
    which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    other_user = factories.UserFactory()
    item = factories.ItemFactory()
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        {
            "user_id": str(other_user.id),
        },
        format="json",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0


@pytest.mark.parametrize("role", ["reader", "editor"])
@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_create_authenticated_reader_or_editor(
    via, role, mock_user_teams
):
    """Readers or editors of an item should not be allowed to create item accesses."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    other_user = factories.UserFactory()
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0
    for new_role in [role[0] for role in models.RoleChoices.choices]:
        response = client.post(
            f"/api/v1.0/items/{item.id!s}/accesses/",
            {
                "user_id": str(other_user.id),
                "role": new_role,
            },
            format="json",
        )

        assert response.status_code == 403

    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_create_authenticated_administrator(via, mock_user_teams):
    """
    Administrators of an item should be able to create item accesses
    except for the "owner" role.
    An email should be sent to the accesses to notify them of the adding.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role="administrator")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role="administrator")

    other_user = factories.UserFactory()
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0
    # It should not be allowed to create an owner access
    response = client.post(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        {
            "user_id": str(other_user.id),
            "role": "owner",
        },
        format="json",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Only owners of a resource can assign other users as owners."
    }
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0

    # It should be allowed to create a lower access
    role = random.choice(
        [role[0] for role in models.RoleChoices.choices if role[0] != "owner"]
    )

    assert len(mail.outbox) == 0

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        {
            "user_id": str(other_user.id),
            "role": role,
        },
        format="json",
    )

    assert response.status_code == 201
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 1
    new_item_access = models.ItemAccess.objects.filter(user=other_user, item=item).get()
    other_user = serializers.UserSerializer(instance=other_user).data
    assert response.json() == {
        "abilities": new_item_access.get_abilities(user),
        "id": str(new_item_access.id),
        "team": "",
        "role": role,
        "user": other_user,
    }
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [other_user["email"]]
    email_content = " ".join(email.body.split())
    assert f"{user.full_name} shared an item with you!" in email_content
    assert (
        f"{user.full_name} ({user.email}) invited you with the role &quot;{role}&quot; "
        f"on the following item: {item.title}"
    ) in email_content
    assert "items/" + str(item.id) + "/" in email_content


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_create_authenticated_owner(via, mock_user_teams):
    """
    Owners of an item should be able to create item accesses whatever the role.
    An email should be sent to the accesses to notify them of the adding.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role="owner")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role="owner")

    other_user = factories.UserFactory()
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0
    role = random.choice([role[0] for role in models.RoleChoices.choices])

    assert len(mail.outbox) == 0

    response = client.post(
        f"/api/v1.0/items/{item.id!s}/accesses/",
        {
            "user_id": str(other_user.id),
            "role": role,
        },
        format="json",
    )

    assert response.status_code == 201
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 1
    new_item_access = models.ItemAccess.objects.filter(user=other_user, item=item).get()
    other_user = serializers.UserSerializer(instance=other_user).data
    assert response.json() == {
        "id": str(new_item_access.id),
        "user": other_user,
        "team": "",
        "role": role,
        "abilities": new_item_access.get_abilities(user),
    }
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [other_user["email"]]
    email_content = " ".join(email.body.split())
    assert f"{user.full_name} shared an item with you!" in email_content
    assert (
        f"{user.full_name} ({user.email}) invited you with the role &quot;{role}&quot; "
        f"on the following item: {item.title}"
    ) in email_content
    assert "items/" + str(item.id) + "/" in email_content
