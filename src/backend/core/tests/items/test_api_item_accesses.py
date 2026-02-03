"""
Test item accesses API endpoints for users in drive's core app.
"""
# pylint: disable=too-many-lines

import random
from uuid import uuid4

import pytest
from lasuite.drf.models.choices import PRIVILEGED_ROLES, RoleChoices
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
    Authenticated users should not be allowed to list item accesses for an item
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
    assert response.json() == []


def test_api_item_accesses_list_unexisting_item():
    """
    Listing item accesses for an unexisting item should return an empty list.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{uuid4()!s}/accesses/")
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
@pytest.mark.parametrize(
    "role",
    [role for role in RoleChoices if role not in PRIVILEGED_ROLES],
)
def test_api_item_accesses_list_authenticated_related_non_privileged(
    via, role, mock_user_teams, django_assert_num_queries
):
    """
    Authenticated users with no privileged role should only be able to list item
    accesses associated with privileged roles for an item, including from ancestors.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Create items structured as a tree
    unreadable_ancestor = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    # make all documents below the grand parent readable without a specific access for the user
    grand_parent = factories.ItemFactory(
        parent=unreadable_ancestor,
        link_reach="authenticated",
        type=models.ItemTypeChoices.FOLDER,
    )
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FILE)

    user_access = None
    if via == USER:
        user_access = models.ItemAccess.objects.create(
            item=item,
            user=user,
            role=role,
        )
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        user_access = models.ItemAccess.objects.create(
            item=item,
            team="lasuite",
            role=role,
        )

    # Create accesses related to each item
    accesses = (
        factories.UserItemAccessFactory(item=unreadable_ancestor),
        factories.UserItemAccessFactory(item=grand_parent),
        factories.UserItemAccessFactory(item=parent),
        factories.UserItemAccessFactory(item=item),
        factories.TeamItemAccessFactory(item=item),
        user_access,
    )
    factories.UserItemAccessFactory(item=child)

    # Accesses for other documents to which the user is related should not be listed either
    other_access = factories.UserItemAccessFactory(user=user)
    factories.UserItemAccessFactory(item=other_access.item)

    with django_assert_num_queries(3):
        response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()

    # Make sure only privileged roles are returned
    privileged_accesses = [acc for acc in accesses if acc.role in PRIVILEGED_ROLES]

    assert len(content) == len(privileged_accesses)

    assert sorted(content, key=lambda x: x["id"]) == sorted(
        [
            {
                "id": str(access.id),
                "item": {
                    "id": str(access.item_id),
                    "path": str(access.item.path),
                    "depth": access.item.depth,
                },
                "user": {
                    "id": str(access.user.id),
                    "full_name": access.user.full_name,
                    "short_name": access.user.short_name,
                }
                if access.user
                else None,
                "team": access.team,
                "role": access.role,
                "max_ancestors_role": None
                if access.item_id == item.id
                else access.role,
                "max_ancestors_role_item_id": None
                if access.item_id == item.id
                else str(access.item_id),
                "max_role": access.role,
                "abilities": access.get_abilities(user),
                "is_explicit": access.item_id == item.id,
            }
            for access in privileged_accesses
        ],
        key=lambda x: x["id"],
    )


@pytest.mark.parametrize("via", VIA)
@pytest.mark.parametrize(
    "role", [role for role in RoleChoices if role in PRIVILEGED_ROLES]
)
def test_api_item_accesses_list_authenticated_related_privileged(
    via, role, mock_user_teams, django_assert_num_queries
):
    """
    Authenticated users with a privileged role should be able to list all
    item accesses whatever the role, including from ancestors.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Create items structured as a tree
    unreadable_ancestor = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    # make all documents below the grand parent readable without a specific access for the user
    grand_parent = factories.ItemFactory(
        parent=unreadable_ancestor,
        link_reach="authenticated",
        type=models.ItemTypeChoices.FOLDER,
    )
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    child = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FILE)

    if via == USER:
        user_access = models.ItemAccess.objects.create(
            item=item,
            user=user,
            role=role,
        )
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        user_access = models.ItemAccess.objects.create(
            item=item,
            team="lasuite",
            role=role,
        )
    else:
        raise RuntimeError()

    # Create accesses related to each item
    ancestors_accesses = [
        # Access on unreadable ancestor should still be listed
        # as the related user gains access to our document
        factories.UserItemAccessFactory(item=unreadable_ancestor),
        factories.UserItemAccessFactory(item=grand_parent),
        factories.UserItemAccessFactory(item=parent),
    ]
    item_accesses = [
        factories.UserItemAccessFactory(item=item),
        factories.TeamItemAccessFactory(item=item),
        factories.UserItemAccessFactory(item=item),
        user_access,
    ]
    factories.UserItemAccessFactory(item=child)

    # Accesses for other documents to which the user is related should not be listed either
    other_access = factories.UserItemAccessFactory(user=user)
    factories.UserItemAccessFactory(item=other_access.item)

    with django_assert_num_queries(3):
        response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 7
    assert sorted(content, key=lambda x: x["id"]) == sorted(
        [
            {
                "id": str(access.id),
                "item": {
                    "id": str(access.item_id),
                    "path": str(access.item.path),
                    "depth": access.item.depth,
                },
                "user": {
                    "id": str(access.user.id),
                    "email": access.user.email,
                    "language": access.user.language,
                    "full_name": access.user.full_name,
                    "short_name": access.user.short_name,
                    "last_release_note_seen": None,
                }
                if access.user
                else None,
                "max_ancestors_role": None
                if access.item_id == item.id
                else access.role,
                "max_ancestors_role_item_id": None
                if access.item_id == item.id
                else str(access.item_id),
                "max_role": access.role,
                "team": access.team,
                "role": access.role,
                "abilities": access.get_abilities(user),
                "is_explicit": access.item_id == item.id,
            }
            for access in ancestors_accesses + item_accesses
        ],
        key=lambda x: x["id"],
    )


def test_api_item_accesses_retrieve_set_role_to_child():
    """Check set_role_to for an item access with no access on the ancestor."""
    user, other_user = factories.UserFactory.create_batch(2)
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent_access = factories.UserItemAccessFactory(
        item=parent, user=user, role="owner"
    )

    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)
    item_access_other_user = factories.UserItemAccessFactory(
        item=item, user=other_user, role="editor"
    )

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 2

    result_dict = {
        result["id"]: result["abilities"]["set_role_to"] for result in content
    }
    assert result_dict[str(item_access_other_user.id)] == [
        "reader",
        "editor",
        "administrator",
        "owner",
    ]
    assert result_dict[str(parent_access.id)] == []

    # Add an access for the other user on the parent
    factories.UserItemAccessFactory(item=parent, user=other_user, role="editor")

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 2

    # the new added access is not present in the result so the list should be the same
    result_dict = {
        result["id"]: result["abilities"]["set_role_to"] for result in content
    }
    assert result_dict[str(item_access_other_user.id)] == [
        "editor",
        "administrator",
        "owner",
    ]
    assert result_dict[str(parent_access.id)] == []


@pytest.mark.parametrize(
    "roles,results",
    [
        [
            ["administrator", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator"],
                ["reader", "editor", "administrator"],
            ],
        ],
        [
            ["owner", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator", "owner"],
                ["reader", "editor", "administrator", "owner"],
            ],
        ],
        [
            ["owner", "reader", "reader", "owner"],
            [
                ["reader", "editor", "administrator", "owner"],
                ["reader", "editor", "administrator", "owner"],
            ],
        ],
    ],
)
def test_api_item_accesses_list_authenticated_related_same_user(roles, results):
    """
    The maximum role accross ancestor items and set_role_to options for
    a given user should be filled as expected.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Create documents structured as a tree
    grand_parent = factories.ItemFactory(
        link_reach="authenticated", type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    # Create accesses for another user
    other_user = factories.UserFactory()
    factories.UserItemAccessFactory(item=grand_parent, user=other_user, role=roles[1])
    factories.UserItemAccessFactory(item=parent, user=other_user, role=roles[2])
    accesses = [
        factories.UserItemAccessFactory(item=item, user=user, role=roles[0]),
        factories.UserItemAccessFactory(item=item, user=other_user, role=roles[3]),
    ]

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 2

    for result in content:
        assert (
            result["max_ancestors_role"] is None
            if result["user"]["id"] == str(user.id)
            else RoleChoices.max(roles[1], roles[2])
        )

    result_dict = {
        result["id"]: result["abilities"]["set_role_to"] for result in content
    }
    assert [result_dict[str(access.id)] for access in accesses] == results


@pytest.mark.parametrize(
    "roles,results",
    [
        [
            ["administrator", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator"],
                ["reader", "editor", "administrator"],
            ],
        ],
        [
            ["owner", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator", "owner"],
                ["reader", "editor", "administrator", "owner"],
            ],
        ],
        [
            ["owner", "reader", "reader", "owner"],
            [
                ["reader", "editor", "administrator", "owner"],
                ["reader", "editor", "administrator", "owner"],
            ],
        ],
        [
            ["reader", "reader", "reader", "owner"],
            [
                ["reader", "editor", "administrator", "owner"],
                ["reader", "editor", "administrator", "owner"],
            ],
        ],
        [
            ["reader", "administrator", "reader", "editor"],
            [
                ["reader", "editor", "administrator"],
                ["administrator"],
            ],
        ],
        [
            ["editor", "editor", "administrator", "editor"],
            [
                ["reader", "editor", "administrator"],
                ["administrator"],
            ],
        ],
    ],
)
def test_api_item_accesses_list_authenticated_related_same_team(
    roles, results, mock_user_teams
):
    """
    The maximum role across ancestor items and set_role_to optionsfor
    a given team should be filled as expected.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    # Create documents structured as a tree
    grand_parent = factories.ItemFactory(
        link_reach="authenticated", type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent, type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    mock_user_teams.return_value = ["lasuite", "unknown"]
    factories.TeamItemAccessFactory(item=grand_parent, team="lasuite", role=roles[1])
    factories.TeamItemAccessFactory(item=parent, team="lasuite", role=roles[2])
    accesses = [
        factories.UserItemAccessFactory(item=item, user=user, role=roles[0]),
        # Create accesses for a team
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=roles[3]),
    ]

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 2

    for result in content:
        assert (
            result["max_ancestors_role"] is None
            if result["user"] and result["user"]["id"] == str(user.id)
            else RoleChoices.max(roles[1], roles[2])
        )

    result_dict = {
        result["id"]: result["abilities"]["set_role_to"] for result in content
    }
    assert [result_dict[str(access.id)] for access in accesses] == results


def test_api_item_accesses_retrieve_anonymous():
    """
    Anonymous users should not be allowed to retrieve an item access.
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
@pytest.mark.parametrize("user_role", PRIVILEGED_ROLES)
def test_api_item_accesses_retrieve_authenticated_related(
    via, user_role, mock_user_teams
):
    """
    A user with privileged role should be allowed to retrieve
    any item access.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    if via == USER:
        factories.UserItemAccessFactory(item=item, user=user, role=user_role)
    elif via == TEAM:
        mock_user_teams.return_value = ["lasuite", "unknown"]
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=user_role)

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
        "max_role": access.role,
        "max_ancestors_role": None,
        "max_ancestors_role_item_id": None,
        "item": {
            "id": str(item.id),
            "path": str(item.path),
            "depth": item.depth,
        },
        "is_explicit": True,
    }


## Update --


def test_api_item_accesses_update_anonymous():
    """Anonymous users should not be allowed to update an item access."""
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
    Authenticated users should not be allowed to update an item access for an item to which
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
    """Readers or editors of an item should not be allowed to update its accesses."""
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
@pytest.mark.parametrize("create_for", VIA)
def test_api_item_accesses_update_administrator_except_owner(
    create_for,
    via,
    mock_user_teams,
):
    """
    A user who is a direct administrator in an item should be allowed to update a user
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
        "role": random.choice(["administrator", "editor", "reader"]),
    }

    if create_for == USER:
        new_values["user_id"] = factories.UserFactory().id
    elif create_for == TEAM:
        new_values["team"] = "new-team"

    for field, value in new_values.items():
        new_data = {**old_values, field: value}
        response = client.put(
            f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
            data=new_data,
            format="json",
        )
        assert response.status_code == 200

        access.refresh_from_db()
        updated_values = serializers.ItemAccessSerializer(instance=access).data
        if field in ["role", "max_role"]:
            assert updated_values == {
                **old_values,
                "role": new_values["role"],
                "max_role": new_values["role"],
            }
        else:
            assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_administrator_from_owner(via, mock_user_teams):
    """
    A user who is an administrator in an item, should not be allowed to update
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
    A user who is an administrator in an item, should not be allowed to update
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
        if field == "role":
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
@pytest.mark.parametrize("create_for", VIA)
def test_api_item_accesses_update_owner(
    create_for,
    via,
    mock_user_teams,
):
    """
    A user who is an owner in an item should be allowed to update
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
        "role": random.choice(models.RoleChoices.values),
    }
    if create_for == USER:
        new_values["user_id"] = factories.UserFactory().id
    elif create_for == TEAM:
        new_values["team"] = "new-team"

    for field, value in new_values.items():
        new_data = {**old_values, field: value}
        response = client.put(
            f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
            data=new_data,
            format="json",
        )
        assert response.status_code == 200

        access.refresh_from_db()
        updated_values = serializers.ItemAccessSerializer(instance=access).data

        if field in ["role", "max_role"]:
            assert updated_values == {
                **old_values,
                "role": new_values["role"],
                "max_role": new_values["role"],
            }
        else:
            assert updated_values == old_values


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_update_owner_self(
    via,
    mock_user_teams,
):
    """
    A user who is owner of an item should be allowed to update
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


def test_api_item_accesses_update_authenticated_owner_explict_accesses():
    """
    An owner of an item should be able to update the accesses of an other user
    if the roles are strictly higher than the previous accesses.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    factories.UserItemAccessFactory(item=root, user=user, role="owner")

    root_access = factories.UserItemAccessFactory(
        item=root, user=other_user, role="editor"
    )
    item_access = factories.UserItemAccessFactory(
        item=item, user=other_user, role="owner"
    )

    # Changing role of item to lower than editor should fail
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/accesses/{item_access.id!s}/",
        data={
            "role": "reader",
        },
        format="json",
    )
    assert response.status_code == 403

    # Changing role of item to higher than editor should success
    response = client.put(
        f"/api/v1.0/items/{item.id!s}/accesses/{item_access.id!s}/",
        data={
            "role": "administrator",
        },
        format="json",
    )
    assert response.status_code == 200

    # Root access can be downgraded to reader

    response = client.put(
        f"/api/v1.0/items/{root.id!s}/accesses/{root_access.id!s}/",
        data={
            "role": "reader",
        },
        format="json",
    )
    assert response.status_code == 200


def test_api_item_accesses_update_authenticated_owner_syncronize_descendants_accesses():
    """
    An owner of an item should be able to update the accesses of an other user
    and syncronize the accesses of the descendants of the item.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    factories.UserItemAccessFactory(item=root, user=user, role="owner")

    root_access = factories.UserItemAccessFactory(
        item=root, user=other_user, role="reader"
    )
    factories.UserItemAccessFactory(item=item, user=other_user, role="editor")

    assert models.ItemAccess.objects.filter(item=item, user=other_user).count() == 1

    # Promote the other user to administrator on the root_access

    response = client.put(
        f"/api/v1.0/items/{root.id!s}/accesses/{root_access.id!s}/",
        data={
            "role": "administrator",
        },
        format="json",
    )
    assert response.status_code == 200

    root_access.refresh_from_db()
    assert root_access.role == "administrator"

    # item_access should be removed
    assert models.ItemAccess.objects.filter(item=item, user=other_user).count() == 0


def test_api_item_accesses_update_authenticated_owner_syncronize_descendants_accesses_same_role():
    """
    An owner of an item should be able to update the accesses of an other user
    and syncronize the accesses of the descendants of the item.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    factories.UserItemAccessFactory(item=root, user=user, role="owner")

    root_access = factories.UserItemAccessFactory(
        item=root, user=other_user, role="reader"
    )
    factories.UserItemAccessFactory(item=item, user=other_user, role="editor")

    assert models.ItemAccess.objects.filter(item=item, user=other_user).count() == 1

    # Promote the other user to editor on the root_access

    response = client.put(
        f"/api/v1.0/items/{root.id!s}/accesses/{root_access.id!s}/",
        data={
            "role": "editor",
        },
        format="json",
    )
    assert response.status_code == 200

    root_access.refresh_from_db()
    assert root_access.role == "editor"

    # item_access should be removed
    assert models.ItemAccess.objects.filter(item=item, user=other_user).count() == 0


def test_api_item_accesses_update_authenticated_owner_syncronize_descendants_accesses_no_lower():
    """
    An owner of an item should be able to update the accesses of an other user
    and syncronize the accesses of the descendants of the item.
    """
    user = factories.UserFactory()
    other_user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    factories.UserItemAccessFactory(item=root, user=user, role="owner")

    root_access = factories.UserItemAccessFactory(
        item=root, user=other_user, role="reader"
    )
    factories.UserItemAccessFactory(item=parent, user=other_user, role="administrator")
    factories.UserItemAccessFactory(item=item, user=other_user, role="owner")

    assert models.ItemAccess.objects.filter(item=item, user=other_user).count() == 1

    # Promote the other user to administrator on the root_access

    response = client.put(
        f"/api/v1.0/items/{root.id!s}/accesses/{root_access.id!s}/",
        data={
            "role": "editor",
        },
        format="json",
    )
    assert response.status_code == 200

    root_access.refresh_from_db()
    assert root_access.role == "editor"

    # item_access should be kept
    assert (
        models.ItemAccess.objects.filter(
            item=item, user=other_user, role="owner"
        ).count()
        == 1
    )
    # parent_access should be kept
    assert (
        models.ItemAccess.objects.filter(
            item=parent, user=other_user, role="administrator"
        ).count()
        == 1
    )


def test_api_item_accesses_update_to_same_role_as_max_ancestors_role():
    """
    If the role is updated and is the same role as the max ancestors role,
    The current access is deleted and a 204 status code is returned.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    # Create an explicit owner access for the current user on the root item
    factories.UserItemAccessFactory(item=root, user=user, role="owner")

    other_user = factories.UserFactory()
    factories.UserItemAccessFactory(item=root, user=other_user, role="editor")
    target_access = factories.UserItemAccessFactory(
        item=item, user=other_user, role="administrator"
    )

    assert item.get_role(other_user) == "administrator"
    assert models.ItemAccess.objects.filter(item=item, user=other_user).exists()

    response = client.put(
        f"/api/v1.0/items/{item.id!s}/accesses/{target_access.id!s}/",
        data={"role": "editor"},
    )

    assert response.status_code == 204

    assert item.get_role(other_user) == "editor"
    assert not models.ItemAccess.objects.filter(item=item, user=other_user).exists()


def test_api_item_accesses_delete_anonymous():
    """Anonymous users should not be allowed to destroy an item access."""
    user = factories.UserFactory()

    item = factories.ItemFactory()
    access = factories.UserItemAccessFactory(user=user, item=item, role="owner")

    response = APIClient().delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 401
    assert models.ItemAccess.objects.count() == 1


def test_api_item_accesses_delete_authenticated():
    """
    Authenticated users should not be allowed to delete an item access for an
    item to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    other_user = factories.UserFactory()
    access = factories.UserItemAccessFactory(user=other_user, item__creator=other_user)

    assert models.ItemAccess.objects.count() == 1
    response = client.delete(
        f"/api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 1


@pytest.mark.parametrize("role", ["reader", "editor"])
@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_reader_or_editor(via, role, mock_user_teams):
    """
    Authenticated users should not be allowed to delete an item access for a
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

    assert models.ItemAccess.objects.count() == 2
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 2


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_administrators_except_owners(
    via,
    mock_user_teams,
):
    """
    Users who are administrators in an item should be allowed to delete an access
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

    assert models.ItemAccess.objects.count() == 2
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 1


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_administrator_on_owners(via, mock_user_teams):
    """
    Users who are administrators in an item should not be allowed to delete an ownership
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

    assert models.ItemAccess.objects.count() == 2
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 2


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_owners(
    via,
    mock_user_teams,
):
    """
    Users should be able to delete the item access of another user
    for an item of which they are owner.
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

    assert models.ItemAccess.objects.count() == 2
    assert models.ItemAccess.objects.filter(user=access.user).exists()

    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 1


@pytest.mark.parametrize("via", VIA)
def test_api_item_accesses_delete_owners_last_owner(via, mock_user_teams):
    """
    It should not be possible to delete the last owner access from an item
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

    assert models.ItemAccess.objects.count() == 1
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 403
    assert models.ItemAccess.objects.count() == 1


def test_api_item_accesses_delete_owners_last_owner_child_user():
    """
    It should be possible to delete the last owner access from an item that is not a root.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent)
    access = factories.UserItemAccessFactory(item=item, user=user, role="owner")

    assert models.ItemAccess.objects.count() == 1
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 0


def test_api_item_accesses_delete_owners_last_owner_child_team(
    mock_user_teams,
):
    """
    It should be possible to delete the last owner access from an item that
    is not a root.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent)
    mock_user_teams.return_value = ["lasuite", "unknown"]
    access = factories.TeamItemAccessFactory(item=item, team="lasuite", role="owner")

    assert models.ItemAccess.objects.count() == 1
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 0


## Realistic case.


def test_api_item_accesses_explicit(django_assert_num_queries):
    """
    test case with a combination of explicit accesses and inherited accesses.
    An explicit access id added on the root item with a "weak" role (editor)
    and then an explicit access is added on the deepest item with a "strong" role (owner).
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    root = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    parent = factories.ItemFactory(parent=root, type=models.ItemTypeChoices.FOLDER)
    item = factories.ItemFactory(parent=parent, type=models.ItemTypeChoices.FOLDER)

    # explicit access on root.
    factories.UserItemAccessFactory(item=root, user=user, role="editor")
    # explicit access on item.
    item_access = factories.UserItemAccessFactory(item=item, user=user, role="owner")
    other_admin_access = factories.UserItemAccessFactory(
        item=root, role="administrator"
    )
    other_owner_access = factories.UserItemAccessFactory(item=root, role="owner")

    assert item.get_role(user) == "owner"

    with django_assert_num_queries(3):
        response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")
    assert response.status_code == 200
    content = response.json()
    assert content == [
        {
            "id": str(other_admin_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(other_admin_access.user.id),
                "email": other_admin_access.user.email,
                "language": other_admin_access.user.language,
                "full_name": other_admin_access.user.full_name,
                "short_name": other_admin_access.user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": False,
                "set_role_to": [],
            },
            "max_ancestors_role": other_admin_access.role,
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
        {
            "id": str(other_owner_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(other_owner_access.user.id),
                "email": other_owner_access.user.email,
                "language": other_owner_access.user.language,
                "full_name": other_owner_access.user.full_name,
                "short_name": other_owner_access.user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": False,
                "set_role_to": [],
            },
            "max_ancestors_role": other_owner_access.role,
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(item_access.id),
            "item": {
                "id": str(item.id),
                "path": str(item.path),
                "depth": item.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["editor", "administrator", "owner"],
            },
            "max_ancestors_role": "editor",
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": True,
        },
    ]

    other_owner = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    owner_access = factories.UserItemAccessFactory(
        item=root, user=other_owner, role="owner"
    )
    factories.UserItemAccessFactory(item=parent, user=user, role="administrator")

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")
    with django_assert_num_queries(3):
        response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    content = response.json()
    assert content == [
        {
            "id": str(other_admin_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(other_admin_access.user.id),
                "email": other_admin_access.user.email,
                "language": other_admin_access.user.language,
                "full_name": other_admin_access.user.full_name,
                "short_name": other_admin_access.user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": False,
                "set_role_to": [],
            },
            "max_ancestors_role": other_admin_access.role,
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
        {
            "id": str(other_owner_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(other_owner_access.user.id),
                "email": other_owner_access.user.email,
                "language": other_owner_access.user.language,
                "full_name": other_owner_access.user.full_name,
                "short_name": other_owner_access.user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": False,
                "set_role_to": [],
            },
            "max_ancestors_role": other_owner_access.role,
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(owner_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(owner_access.user.id),
                "email": owner_access.user.email,
                "language": owner_access.user.language,
                "full_name": owner_access.user.full_name,
                "short_name": owner_access.user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": False,
                "set_role_to": [],
            },
            "max_ancestors_role": owner_access.role,
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(item_access.id),
            "item": {
                "id": str(item.id),
                "path": str(item.path),
                "depth": item.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["administrator", "owner"],
            },
            "max_ancestors_role": "administrator",
            "max_ancestors_role_item_id": str(parent.id),
            "max_role": "owner",
            "is_explicit": True,
        },
    ]


def test_api_item_accesses_other_user_accesses():
    """Check the abilities of a user when other users have accesses on the same item."""
    user = factories.UserFactory()
    other_user = factories.UserFactory()

    grand_parent = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER, title="A")
    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, title="B", parent=grand_parent
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, title="C", parent=parent
    )

    user_access = factories.UserItemAccessFactory(
        item=grand_parent, user=user, role="owner"
    )
    other_user_access = factories.UserItemAccessFactory(
        item=grand_parent, user=other_user, role="administrator"
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()

    assert content == [
        {
            "id": str(user_access.id),
            "item": {
                "id": str(grand_parent.id),
                "path": str(grand_parent.path),
                "depth": grand_parent.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": "owner",
            "max_ancestors_role_item_id": str(grand_parent.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(other_user_access.id),
            "item": {
                "id": str(grand_parent.id),
                "path": str(grand_parent.path),
                "depth": grand_parent.depth,
            },
            "user": {
                "id": str(other_user.id),
                "email": other_user.email,
                "language": other_user.language,
                "full_name": other_user.full_name,
                "short_name": other_user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["owner"],
            },
            "max_ancestors_role": "administrator",
            "max_ancestors_role_item_id": str(grand_parent.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
    ]


def test_api_item_accesses_with_inherited_accesses():
    """Test the list of item accesses with inherited accesses."""

    user = factories.UserFactory()

    collaborator = factories.UserFactory()

    grand_parent_access = factories.UserItemAccessFactory(
        item__title="A",
        item__creator=user,
        user=user,
        role=models.RoleChoices.OWNER,
        item__type=models.ItemTypeChoices.FOLDER,
    )
    grand_parent = grand_parent_access.item
    parent = factories.ItemFactory(
        title="B",
        parent=grand_parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        title="C",
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
    )

    factories.UserItemAccessFactory(item=grand_parent, user=collaborator, role="reader")
    administrator_access = factories.UserItemAccessFactory(
        item=parent, user=collaborator, role="administrator"
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()

    assert content == [
        {
            "id": str(grand_parent_access.id),
            "item": {
                "id": str(grand_parent.id),
                "path": str(grand_parent.path),
                "depth": grand_parent.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": "owner",
            "max_ancestors_role_item_id": str(grand_parent.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(administrator_access.id),
            "item": {
                "id": str(parent.id),
                "path": str(parent.path),
                "depth": parent.depth,
            },
            "user": {
                "id": str(collaborator.id),
                "email": collaborator.email,
                "language": collaborator.language,
                "full_name": collaborator.full_name,
                "short_name": collaborator.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["owner"],
            },
            "max_ancestors_role": "administrator",
            "max_ancestors_role_item_id": str(parent.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
    ]


def test_api_item_accesses_inherited_from_root():
    """
    Test the max_ancestors_role and max_ancestors_role_item_id for accesses depending
    of the context it is called from.
    """
    user = factories.UserFactory()
    collaborator = factories.UserFactory()

    root = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, title="A", creator=user
    )
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, title="B", parent=root, creator=user
    )

    user_root_access = factories.UserItemAccessFactory(
        item=root, user=user, role="owner"
    )
    collaborator_root_access = factories.UserItemAccessFactory(
        item=root, user=collaborator, role="administrator"
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{root.id!s}/accesses/")
    assert response.status_code == 200
    content = response.json()

    assert content == [
        {
            "id": str(user_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": None,
            "max_ancestors_role_item_id": None,
            "max_role": "owner",
            "is_explicit": True,
        },
        {
            "id": str(collaborator_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(collaborator.id),
                "email": collaborator.email,
                "language": collaborator.language,
                "full_name": collaborator.full_name,
                "short_name": collaborator.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["reader", "editor", "administrator", "owner"],
            },
            "max_ancestors_role": None,
            "max_ancestors_role_item_id": None,
            "max_role": "administrator",
            "is_explicit": True,
        },
    ]

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()

    assert content == [
        {
            "id": str(user_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": "owner",
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(collaborator_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(collaborator.id),
                "email": collaborator.email,
                "language": collaborator.language,
                "full_name": collaborator.full_name,
                "short_name": collaborator.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["owner"],
            },
            "max_ancestors_role": "administrator",
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
    ]


def test_api_item_accesses_in_tree():
    """
    Test list accesses when a user has access only on a subtree.
    """

    user = factories.UserFactory()
    collaborator = factories.UserFactory()

    root = factories.ItemFactory(creator=user, type=models.ItemTypeChoices.FOLDER)
    user_root_access = factories.UserItemAccessFactory(
        item=root, user=user, role=models.RoleChoices.OWNER
    )

    # user has inherited access on this item and collaborator will have an explicit one.
    folder1 = factories.ItemFactory(
        parent=root, creator=user, type=models.ItemTypeChoices.FOLDER
    )
    collaborator_folder1_access = factories.UserItemAccessFactory(
        item=folder1, user=collaborator, role=models.RoleChoices.ADMIN
    )

    # Both user have inherited access on this file
    file1 = factories.ItemFactory(
        parent=folder1, type=models.ItemTypeChoices.FILE, creator=collaborator
    )

    # Create a client for the owner user
    client = APIClient()
    client.force_login(user)

    # First accesses on folder1 for user
    response = client.get(f"/api/v1.0/items/{folder1.id!s}/accesses/")
    assert response.status_code == 200

    content = response.json()

    assert content == [
        {
            "id": str(user_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": "owner",
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(collaborator_folder1_access.id),
            "item": {
                "id": str(folder1.id),
                "path": str(folder1.path),
                "depth": folder1.depth,
            },
            "user": {
                "id": str(collaborator.id),
                "email": collaborator.email,
                "language": collaborator.language,
                "full_name": collaborator.full_name,
                "short_name": collaborator.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["reader", "editor", "administrator", "owner"],
            },
            "max_ancestors_role": None,
            "max_ancestors_role_item_id": None,
            "max_role": "administrator",
            "is_explicit": True,
        },
    ]

    # Then accesses on file1 for user
    response = client.get(f"/api/v1.0/items/{file1.id!s}/accesses/")
    assert response.status_code == 200

    content = response.json()

    assert content == [
        {
            "id": str(user_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": "owner",
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(collaborator_folder1_access.id),
            "item": {
                "id": str(folder1.id),
                "path": str(folder1.path),
                "depth": folder1.depth,
            },
            "user": {
                "id": str(collaborator.id),
                "email": collaborator.email,
                "language": collaborator.language,
                "full_name": collaborator.full_name,
                "short_name": collaborator.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": True,
                "partial_update": True,
                "retrieve": True,
                "set_role_to": ["owner"],
            },
            "max_ancestors_role": "administrator",
            "max_ancestors_role_item_id": str(folder1.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
    ]

    client = APIClient()
    client.force_login(collaborator)

    response = client.get(f"/api/v1.0/items/{file1.id!s}/accesses/")
    assert response.status_code == 200

    content = response.json()

    assert len(content) == 2

    assert content == [
        {
            "id": str(user_root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "language": user.language,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "owner",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": False,
                "set_role_to": [],
            },
            "max_ancestors_role": "owner",
            "max_ancestors_role_item_id": str(root.id),
            "max_role": "owner",
            "is_explicit": False,
        },
        {
            "id": str(collaborator_folder1_access.id),
            "item": {
                "id": str(folder1.id),
                "path": str(folder1.path),
                "depth": folder1.depth,
            },
            "user": {
                "id": str(collaborator.id),
                "email": collaborator.email,
                "language": collaborator.language,
                "full_name": collaborator.full_name,
                "short_name": collaborator.short_name,
                "last_release_note_seen": None,
            },
            "team": "",
            "role": "administrator",
            "abilities": {
                "destroy": True,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": "administrator",
            "max_ancestors_role_item_id": str(folder1.id),
            "max_role": "administrator",
            "is_explicit": False,
        },
    ]
