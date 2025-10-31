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

    with django_assert_num_queries(4):
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
                "max_ancestors_role": None,
                "max_role": access.role,
                "abilities": access.get_abilities(user),
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

    with django_assert_num_queries(4):
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
                }
                if access.user
                else None,
                "max_ancestors_role": None,
                "max_role": access.role,
                "team": access.team,
                "role": access.role,
                "abilities": access.get_abilities(user),
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
    parent_access_other_user = factories.UserItemAccessFactory(
        item=parent, user=other_user, role="editor"
    )

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 3

    result_dict = {
        result["id"]: result["abilities"]["set_role_to"] for result in content
    }
    assert result_dict[str(item_access_other_user.id)] == [
        "administrator",
        "owner",
    ]
    assert result_dict[str(parent_access.id)] == []
    assert result_dict[str(parent_access_other_user.id)] == [
        "reader",
        "editor",
        "administrator",
        "owner",
    ]


@pytest.mark.parametrize(
    "roles,results",
    [
        [
            ["administrator", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator"],
                [],
                [],
                ["editor", "administrator"],
            ],
        ],
        [
            ["owner", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator", "owner"],
                [],
                [],
                ["editor", "administrator", "owner"],
            ],
        ],
        [
            ["owner", "reader", "reader", "owner"],
            [
                ["reader", "editor", "administrator", "owner"],
                [],
                [],
                ["editor", "administrator", "owner"],
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
    accesses = [
        factories.UserItemAccessFactory(item=item, user=user, role=roles[0]),
        factories.UserItemAccessFactory(
            item=grand_parent, user=other_user, role=roles[1]
        ),
        factories.UserItemAccessFactory(item=parent, user=other_user, role=roles[2]),
        factories.UserItemAccessFactory(item=item, user=other_user, role=roles[3]),
    ]

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 4

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
                [],
                [],
                ["editor", "administrator"],
            ],
        ],
        [
            ["owner", "reader", "reader", "reader"],
            [
                ["reader", "editor", "administrator", "owner"],
                [],
                [],
                ["editor", "administrator", "owner"],
            ],
        ],
        [
            ["owner", "reader", "reader", "owner"],
            [
                ["reader", "editor", "administrator", "owner"],
                [],
                [],
                ["editor", "administrator", "owner"],
            ],
        ],
        [
            ["reader", "reader", "reader", "owner"],
            [
                ["reader", "editor", "administrator", "owner"],
                [],
                [],
                ["editor", "administrator", "owner"],
            ],
        ],
        [
            ["reader", "administrator", "reader", "editor"],
            [
                ["reader", "editor", "administrator"],
                ["reader", "editor", "administrator"],
                [],
                [],
            ],
        ],
        [
            ["editor", "editor", "administrator", "editor"],
            [
                ["reader", "editor", "administrator"],
                [],
                [],
                [],
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
    accesses = [
        factories.UserItemAccessFactory(item=item, user=user, role=roles[0]),
        # Create accesses for a team
        factories.TeamItemAccessFactory(
            item=grand_parent, team="lasuite", role=roles[1]
        ),
        factories.TeamItemAccessFactory(item=parent, team="lasuite", role=roles[2]),
        factories.TeamItemAccessFactory(item=item, team="lasuite", role=roles[3]),
    ]

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    assert len(content) == 4

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
        "item": {
            "id": str(item.id),
            "path": str(item.path),
            "depth": item.depth,
        },
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

    assert models.ItemAccess.objects.count() == 4
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 3


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

    assert models.ItemAccess.objects.count() == 4
    response = client.delete(
        f"/api/v1.0/items/{item.id!s}/accesses/{access.id!s}/",
    )

    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == 3


## Realistic case.


def test_api_item_accesses_explicit():
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
    root_access = factories.UserItemAccessFactory(item=root, user=user, role="editor")
    # explicit access on item.
    item_access = factories.UserItemAccessFactory(item=item, user=user, role="owner")
    other_admin_access = factories.UserItemAccessFactory(
        item=root, role="administrator"
    )
    other_owner_access = factories.UserItemAccessFactory(item=root, role="owner")

    assert item.get_role(user) == "owner"

    response = client.get(f"/api/v1.0/items/{item.id!s}/accesses/")
    assert response.status_code == 200
    content = response.json()

    assert content == [
        {
            "id": str(root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "language": user.language,
            },
            "team": "",
            "role": "editor",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": None,
            "max_role": "editor",
        },
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
            "max_ancestors_role": None,
            "max_role": "administrator",
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
            "max_ancestors_role": None,
            "max_role": "owner",
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
            "max_ancestors_role": "editor",
            "max_role": "owner",
        },
    ]

    other_owner = factories.UserFactory()
    client = APIClient()
    client.force_login(user)
    owner_access = factories.UserItemAccessFactory(
        item=root, user=other_owner, role="owner"
    )

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
            "max_ancestors_role": None,
            "max_role": "administrator",
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
            "max_ancestors_role": None,
            "max_role": "owner",
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
            "max_ancestors_role": None,
            "max_role": "owner",
        },
        {
            "id": str(root_access.id),
            "item": {
                "id": str(root.id),
                "path": str(root.path),
                "depth": root.depth,
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "short_name": user.short_name,
                "language": user.language,
            },
            "team": "",
            "role": "editor",
            "abilities": {
                "destroy": False,
                "update": False,
                "partial_update": False,
                "retrieve": True,
                "set_role_to": [],
            },
            "max_ancestors_role": None,
            "max_role": "editor",
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
            "max_ancestors_role": "editor",
            "max_role": "owner",
        },
    ]
