"""
Test item accesses API endpoints for users in drive's core app.
"""

import random
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.api import serializers
from core.tests.conftest import TEAM, USER, VIA

pytestmark = pytest.mark.django_db


def test_api_item_accesses_list_anonymous():
    """Anonymous users should not be allowed to list item accesses."""
    item = factories.ItemFactory()
    factories.UserItemAccessFactory.create_batch(2, item=item)

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/accesses/")
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


def test_api_item_accesses_list_authenticated_unrelated():
    """
    Authenticated users should not be allowed to list item accesses for a item
    to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    factories.UserItemAccessFactory.create_batch(3, item=item)

    # Accesses for other items to which the user is related should not be listed either
    other_access = factories.UserItemAccessFactory(user=user)
    factories.UserItemAccessFactory(item=other_access.item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/accesses/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_list_authenticated_related(via, mock_user_teams):
    """
    Authenticated users should be able to list item accesses for a item
    to which they are directly related, whatever their role in the item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    user_access = None
    if via == USER:
        user_access = models.ItemAccess.objects.create(
            item=item,
            user=user,
            role=random.choice(models.RoleChoices.values),
        )
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        user_access = models.ItemAccess.objects.create(
            item=item,
            team="lasuite",
            role=random.choice(models.RoleChoices.values),
        )

    access1 = factories.TeamItemAccessFactory(item=item)
    access2 = factories.UserItemAccessFactory(item=item)

    # Accesses for other items to which the user is related should not be listed either
    other_access = factories.UserItemAccessFactory(user=user)
    factories.UserItemAccessFactory(item=other_access.item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/accesses/",
    )

    access2_user = serializers.UserSerializer(instance=access2.user).data
    base_user = serializers.UserSerializer(instance=user).data

    assert response.status_code == 200
    content = response.json()
    assert len(content["results"]) == 3
    assert sorted(content["results"], key=lambda x: x["id"]) == sorted(
        [
            {
                "id": str(user_access.id),
                "user": base_user if via == "user" else None,
                "team": "lasuite" if via == "team" else "",
                "role": user_access.role,
                "abilities": user_access.get_abilities(user),
            },
            {
                "id": str(access1.id),
                "user": None,
                "team": access1.team,
                "role": access1.role,
                "abilities": access1.get_abilities(user),
            },
            {
                "id": str(access2.id),
                "user": access2_user,
                "team": "",
                "role": access2.role,
                "abilities": access2.get_abilities(user),
            },
        ],
        key=lambda x: x["id"],
    )


def test_api_item_accesses_retrieve_anonymous():
    """
    Anonymous users should not be allowed to retrieve a item access.
    """
    access = factories.UserItemAccessFactory()

    response = APIClient().get(
        f"/api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
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


def test_api_item_accesses_retrieve_authenticated_unrelated():
    """
    Authenticated users should not be allowed to retrieve an item access for
    an item to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    access = factories.UserItemAccessFactory(item=item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )
    assert response.status_code == 403
    assert response.json() == {
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }

    # Accesses related to another item should be excluded even if the user is related to it
    for access in [
        factories.UserItemAccessFactory(),
        factories.UserItemAccessFactory(user=user),
    ]:
        response = client.get(
            f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
        )

        assert response.status_code == 404
        assert response.json() == {
            "errors": [
                {
                    "attr": None,
                    "code": "not_found",
                    "detail": "Not found.",
                },
            ],
            "type": "client_error",
        }


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_retrieve_authenticated_related(via, mock_user_teams):
    """
    A user who is related to a item should be allowed to retrieve the
    associated item user accesses.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite")

    access = factories.UserItemAccessFactory(item=item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    access_user = serializers.UserSerializer(instance=access.user).data

    assert response.status_code == 200
    assert response.json() == {
        "id": str(access.id),
        "user": access_user,
        "team": "",
        "role": access.role,
        "abilities": access.get_abilities(user),
    }


def test_api_item_accesses_update_anonymous():
    """Anonymous users should not be allowed to update a item access."""
    access = factories.UserItemAccessFactory()
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user": factories.UserFactory().id,
        "role": random.choice(models.RoleChoices.values),
    }

    api_client = APIClient()
    for field, value in new_values.items():
        response = api_client.put(
            f"/api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
            {**old_values, field: value},
            format="json",
        )
        assert response.status_code == 401

    access.refresh_from_db()
    updated_values = serializers.ItemAccessSerializer(instance=access).data
    assert updated_values == old_values


def test_api_item_accesses_update_authenticated_unrelated():
    """
    Authenticated users should not be allowed to update a item access for a item to which
    they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    access = factories.UserItemAccessFactory()
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user": factories.UserFactory().id,
        "role": random.choice(models.RoleChoices.values),
    }

    for field, value in new_values.items():
        response = client.put(
            f"/api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
            {**old_values, field: value},
            format="json",
        )
        assert response.status_code == 403

    access.refresh_from_db()
    updated_values = serializers.ItemAccessSerializer(instance=access).data
    assert updated_values == old_values


@pytest.mark.parametrize("role", ["reader", "editor"])
@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_authenticated_reader_or_editor(
    via, role, mock_user_teams
):
    """Readers or editors of a item should not be allowed to update its accesses."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access = factories.UserItemAccessFactory(item=item)
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user": factories.UserFactory().id,
        "role": random.choice(models.RoleChoices.values),
    }

    for field, value in new_values.items():
        response = client.put(
            f"/api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
            {**old_values, field: value},
            format="json",
        )
        assert response.status_code == 403

    access.refresh_from_db()
    updated_values = serializers.ItemAccessSerializer(instance=access).data
    assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_administrator_except_owner(
    via,
    mock_user_teams,
):
    """
    A user who is a direct administrator in a item should be allowed to update a user
    access for this item, as long as they don't try to set the role to owner.
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

    access = factories.UserItemAccessFactory(
        item=item,
        role=random.choice(["administrator", "editor", "reader"]),
    )
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user_id": factories.UserFactory().id,
        "role": random.choice(["administrator", "editor", "reader"]),
    }

    for field, value in new_values.items():
        new_data = {**old_values, field: value}
        if new_data["role"] == old_values["role"]:
            response = client.put(
                f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
                data=new_data,
                format="json",
            )
            assert response.status_code == 403
        else:
            response = client.put(
                f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
                data=new_data,
                format="json",
            )
            assert response.status_code == 200

        access.refresh_from_db()
        updated_values = serializers.ItemAccessSerializer(instance=access).data
        if field == "role":
            assert updated_values == {**old_values, "role": new_values["role"]}
        else:
            assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_administrator_from_owner(via, mock_user_teams):
    """
    A user who is an administrator in a item, should not be allowed to update
    the user access of an "owner" for this item.
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
    access = factories.UserItemAccessFactory(item=item, user=other_user, role="owner")
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user_id": factories.UserFactory().id,
        "role": random.choice(models.RoleChoices.values),
    }

    for field, value in new_values.items():
        response = client.put(
            f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
            data={**old_values, field: value},
            format="json",
        )

        assert response.status_code == 403
        access.refresh_from_db()
        updated_values = serializers.ItemAccessSerializer(instance=access).data
        assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_administrator_to_owner(
    via,
    mock_user_teams,
):
    """
    A user who is an administrator in a item, should not be allowed to update
    the user access of another user to grant item ownership.
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
    access = factories.UserItemAccessFactory(
        item=item,
        user=other_user,
        role=random.choice(["administrator", "editor", "reader"]),
    )
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user_id": factories.UserFactory().id,
        "role": "owner",
    }

    for field, value in new_values.items():
        new_data = {**old_values, field: value}
        # We are not allowed or not really updating the role
        if field == "role" or new_data["role"] == old_values["role"]:
            response = client.put(
                f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
                data=new_data,
                format="json",
            )

            assert response.status_code == 403
        else:
            response = client.put(
                f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
                data=new_data,
                format="json",
            )
            assert response.status_code == 200

        access.refresh_from_db()
        updated_values = serializers.ItemAccessSerializer(instance=access).data
        assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_owner(
    via,
    mock_user_teams,
):
    """
    A user who is an owner in a item should be allowed to update
    a user access for this item whatever the role.
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

    factories.UserFactory()
    access = factories.UserItemAccessFactory(
        item=item,
    )
    old_values = serializers.ItemAccessSerializer(instance=access).data

    new_values = {
        "id": uuid4(),
        "user_id": factories.UserFactory().id,
        "role": random.choice(models.RoleChoices.values),
    }

    for field, value in new_values.items():
        new_data = {**old_values, field: value}
        if (
            new_data["role"] == old_values["role"]
        ):  # we are not really updating the role
            response = client.put(
                f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
                data=new_data,
                format="json",
            )
            assert response.status_code == 403
        else:
            response = client.put(
                f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
                data=new_data,
                format="json",
            )

            assert response.status_code == 200

        access.refresh_from_db()
        updated_values = serializers.ItemAccessSerializer(instance=access).data

        if field == "role":
            assert updated_values == {**old_values, "role": new_values["role"]}
        else:
            assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_owner_self(
    via,
    mock_user_teams,
):
    """
    A user who is owner of a item should be allowed to update
    their own user access provided there are other owners in the item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    access = None
    if via == USER:
        access = factories.UserItemAccessFactory(item=item, user=user, role="owner")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        access = factories.TeamItemAccessFactory(
            item=item, team="lasuite", role="owner"
        )

    old_values = serializers.ItemAccessSerializer(instance=access).data
    new_role = random.choice(["administrator", "editor", "reader"])

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
        data={**old_values, "role": new_role},
        format="json",
    )

    assert response.status_code == 403
    access.refresh_from_db()
    assert access.role == "owner"

    # Add another owner and it should now work
    factories.UserItemAccessFactory(item=item, role="owner")

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
        data={
            **old_values,
            "role": new_role,
            "user_id": old_values.get("user", {}).get("id")
            if old_values.get("user") is not None
            else None,
        },
        format="json",
    )

    assert response.status_code == 200
    access.refresh_from_db()
    assert access.role == new_role


# Delete


def test_api_item_accesses_delete_anonymous():
    """Anonymous users should not be allowed to destroy a item access."""
    user = factories.UserFactory()
    item = user.get_main_workspace()
    access = models.ItemAccess.objects.get(user=user, role="owner", item=item)

    response = APIClient().delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 401
    assert models.ItemAccess.objects.count() == 1


def test_api_item_accesses_delete_authenticated():
    """
    Authenticated users should not be allowed to delete a item access for a
    item to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    other_user = factories.UserFactory()
    access = factories.UserItemAccessFactory(user=other_user, item__creator=other_user)

    assert models.ItemAccess.objects.count() == 3
    response = client.delete(
        f"/api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 3


@pytest.mark.parametrize("role", ["reader", "editor"])
@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_reader_or_editor(via, role, mock_user_teams):
    """
    Authenticated users should not be allowed to delete a item access for a
    item in which they are a simple reader or editor.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=role)

    access = factories.UserItemAccessFactory(item=item)

    assert models.ItemAccess.objects.count() == 5
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 5


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_administrators_except_owners(
    via,
    mock_user_teams,
):
    """
    Users who are administrators in a item should be allowed to delete an access
    from the item provided it is not ownership.
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

    access = factories.UserItemAccessFactory(
        item=item, role=random.choice(["reader", "editor", "administrator"])
    )

    assert models.ItemAccess.objects.count() == 5
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 4


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_administrator_on_owners(via, mock_user_teams):
    """
    Users who are administrators in a item should not be allowed to delete an ownership
    access from the item.
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

    access = factories.UserItemAccessFactory(item=item, role="owner")

    assert models.ItemAccess.objects.count() == 5
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 5


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_owners(
    via,
    mock_user_teams,
):
    """
    Users should be able to delete the item access of another user
    for a item of which they are owner.
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

    access = factories.UserItemAccessFactory(item=item)

    assert models.ItemAccess.objects.count() == 5
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 4


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_owners_last_owner(via, mock_user_teams):
    """
    It should not be possible to delete the last owner access from a item
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(creator=user)
    access = None
    if via == USER:
        access = factories.UserItemAccessFactory(item=item, user=user, role="owner")
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        access = factories.TeamItemAccessFactory(
            item=item, team="lasuite", role="owner"
        )

    assert models.ItemAccess.objects.count() == 2
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 2
