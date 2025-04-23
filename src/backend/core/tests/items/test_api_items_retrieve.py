"""
Tests for items API endpoint in drive's core app: retrieve
"""

# pylint: disable=too-many-lines
import random
from datetime import timedelta
from unittest import mock

from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_retrieve_anonymous_public_standalone():
    """Anonymous users should be allowed to retrieve public items."""
    item = factories.ItemFactory(link_reach="public")

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": {
            "accesses_manage": False,
            "accesses_view": False,
            "children_create": False,
            "children_list": True,
            "destroy": False,
            # Anonymous user can't favorite an item even with read access
            "favorite": False,
            "invite_owner": False,
            "link_configuration": False,
            "media_auth": True,
            "move": False,
            "partial_update": False,
            "restore": False,
            "retrieve": True,
            "tree": True,
            "update": False,
            "upload_ended": False,
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 1,
        "is_favorite": False,
        "link_reach": "public",
        "link_role": item.link_role,
        "nb_accesses": 0,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


def test_api_items_retrieve_anonymous_public_parent():
    """Anonymous users should be allowed to retrieve an item who has a public ancestor."""
    grand_parent = factories.ItemFactory(
        link_reach="public", type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        link_reach=random.choice(["authenticated", "restricted"]),
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        link_reach=random.choice(["authenticated", "restricted"]), parent=parent
    )

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": {
            "accesses_manage": False,
            "accesses_view": False,
            "children_create": False,
            "children_list": True,
            "destroy": grand_parent.link_role == "editor",
            # Anonymous user can't favorite an item even with read access
            "favorite": False,
            "invite_owner": False,
            "link_configuration": False,
            "media_auth": True,
            "move": grand_parent.link_role == "editor",
            "partial_update": grand_parent.link_role == "editor",
            "restore": False,
            "retrieve": True,
            "tree": True,
            "update": grand_parent.link_role == "editor",
            "upload_ended": False,
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 3,
        "is_favorite": False,
        "link_reach": item.link_reach,
        "link_role": item.link_role,
        "nb_accesses": 0,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


def test_api_items_retrieve_anonymous_public_child():
    """
    Anonymous users having access to an item should not gain access to a parent item.
    """
    item = factories.ItemFactory(
        link_reach=random.choice(["authenticated", "restricted"]),
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.ItemFactory(link_reach="public", parent=item)

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.parametrize("reach", ["restricted", "authenticated"])
def test_api_items_retrieve_anonymous_restricted_or_authenticated(reach):
    """Anonymous users should not be able to retrieve an item that is not public."""
    item = factories.ItemFactory(link_reach=reach)

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_retrieve_authenticated_unrelated_public_or_authenticated(reach):
    """
    Authenticated users should be able to retrieve a public/authenticated item to
    which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=reach)
    power_roles = ["administrator", "owner"]

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": {
            "accesses_manage": False,
            "accesses_view": False,
            "children_create": item.link_role == "editor",
            "children_list": True,
            "destroy": False,
            "favorite": True,
            "invite_owner": False,
            "link_configuration": False,
            "media_auth": True,
            "move": False,
            "partial_update": item.link_role in power_roles,
            "restore": False,
            "retrieve": True,
            "tree": True,
            "update": item.link_role in power_roles,
            "upload_ended": item.link_role in [*power_roles, "editor"],
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 1,
        "is_favorite": False,
        "link_reach": reach,
        "link_role": item.link_role,
        "nb_accesses": 0,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }
    assert models.LinkTrace.objects.filter(item=item, user=user).exists() is True


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_retrieve_authenticated_public_or_authenticated_parent(reach):
    """
    Authenticated users should be allowed to retrieve an item who has a public or
    authenticated ancestor.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    grand_parent = factories.ItemFactory(
        link_reach=reach, type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent, link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(link_reach="restricted", parent=parent)

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": {
            "accesses_manage": False,
            "accesses_view": False,
            "children_create": grand_parent.link_role == "editor",
            "children_list": True,
            "destroy": grand_parent.link_role == "editor",
            "favorite": True,
            "invite_owner": False,
            "link_configuration": False,
            "move": grand_parent.link_role == "editor",
            "media_auth": True,
            "partial_update": grand_parent.link_role == "editor",
            "restore": False,
            "retrieve": True,
            "tree": True,
            "update": grand_parent.link_role == "editor",
            "upload_ended": grand_parent.link_role == "editor",
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 3,
        "is_favorite": False,
        "link_reach": item.link_reach,
        "link_role": item.link_role,
        "nb_accesses": 0,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_retrieve_authenticated_public_or_authenticated_child(reach):
    """
    Authenticated users having access to an item should not gain access to a parent item.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory(link_reach=reach, parent=item)

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_retrieve_authenticated_trace_twice(reach):
    """
    Accessing an item several times should not raise any error even though the
    trace already exists for this item and user.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=reach)
    assert models.LinkTrace.objects.filter(item=item, user=user).exists() is False

    client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert models.LinkTrace.objects.filter(item=item, user=user).exists() is True

    # A second visit should not raise any error
    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200


def test_api_items_retrieve_authenticated_unrelated_restricted():
    """
    Authenticated users should not be allowed to retrieve an item that is restricted and
    to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted")

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_api_items_retrieve_authenticated_related_direct():
    """
    Authenticated users should be allowed to retrieve an item to which they
    are directly related whatever the role.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory()
    access = factories.UserItemAccessFactory(item=item, user=user)
    factories.UserItemAccessFactory(item=item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": item.get_abilities(user),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "depth": 1,
        "is_favorite": False,
        "link_reach": item.link_reach,
        "link_role": item.link_role,
        "nb_accesses": 2,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [access.role],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


def test_api_items_retrieve_authenticated_related_parent():
    """
    Authenticated users should be allowed to retrieve an item if they are related
    to one of its ancestors whatever the role.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    grand_parent = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent, link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, link_reach="restricted")

    access = factories.UserItemAccessFactory(item=grand_parent, user=user)
    factories.UserItemAccessFactory(item=grand_parent)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": {
            "accesses_manage": access.role in ["administrator", "owner"],
            "accesses_view": True,
            "children_create": access.role != "reader",
            "children_list": True,
            "destroy": access.role != "reader",
            "favorite": True,
            "invite_owner": access.role == "owner",
            "link_configuration": access.role in ["administrator", "owner"],
            "media_auth": True,
            "move": access.role in ["administrator", "owner", "editor"],
            "partial_update": access.role != "reader",
            "restore": access.role == "owner",
            "retrieve": True,
            "tree": True,
            "update": access.role != "reader",
            "upload_ended": access.role != "reader",
        },
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "depth": 3,
        "is_favorite": False,
        "link_reach": "restricted",
        "link_role": item.link_role,
        "nb_accesses": 2,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [access.role],
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


def test_api_items_retrieve_authenticated_related_nb_accesses():
    """Validate computation of number of accesses."""
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    grand_parent = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent, link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    item = factories.ItemFactory(parent=parent, link_reach="restricted")

    factories.UserItemAccessFactory(item=grand_parent, user=user)
    factories.UserItemAccessFactory(item=parent)
    factories.UserItemAccessFactory(item=item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 200
    assert response.json()["nb_accesses"] == 3

    factories.UserItemAccessFactory(item=grand_parent)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 200
    assert response.json()["nb_accesses"] == 4


def test_api_items_retrieve_authenticated_related_child():
    """
    Authenticated users should not be allowed to retrieve an item as a result of being
    related to one of its children.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    child = factories.ItemFactory(parent=item)

    factories.UserItemAccessFactory(item=child, user=user)
    factories.UserItemAccessFactory(item=item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/",
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_api_items_retrieve_authenticated_related_team_none(mock_user_teams):
    """
    Authenticated users should not be able to retrieve a restricted item related to
    teams in which the user is not.
    """
    mock_user_teams.return_value = []

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted")

    factories.TeamItemAccessFactory(item=item, team="readers", role="reader")
    factories.TeamItemAccessFactory(item=item, team="editors", role="editor")
    factories.TeamItemAccessFactory(
        item=item, team="administrators", role="administrator"
    )
    factories.TeamItemAccessFactory(item=item, team="owners", role="owner")
    factories.TeamItemAccessFactory(item=item)
    factories.TeamItemAccessFactory()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.parametrize(
    "teams,roles",
    [
        [["readers"], ["reader"]],
        [["unknown", "readers"], ["reader"]],
        [["editors"], ["editor"]],
        [["unknown", "editors"], ["editor"]],
    ],
)
def test_api_items_retrieve_authenticated_related_team_members(
    teams, roles, mock_user_teams
):
    """
    Authenticated users should be allowed to retrieve an item to which they
    are related via a team whatever the role.
    """
    mock_user_teams.return_value = teams

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted")

    factories.TeamItemAccessFactory(item=item, team="readers", role="reader")
    factories.TeamItemAccessFactory(item=item, team="editors", role="editor")
    factories.TeamItemAccessFactory(
        item=item, team="administrators", role="administrator"
    )
    factories.TeamItemAccessFactory(item=item, team="owners", role="owner")
    factories.TeamItemAccessFactory(item=item)
    factories.TeamItemAccessFactory()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    # pylint: disable=R0801
    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": item.get_abilities(user),
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 1,
        "is_favorite": False,
        "link_reach": "restricted",
        "link_role": item.link_role,
        "nb_accesses": 5,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": roles,
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


@pytest.mark.parametrize(
    "teams,roles",
    [
        [["administrators"], ["administrator"]],
        [["editors", "administrators"], ["administrator", "editor"]],
        [["unknown", "administrators"], ["administrator"]],
    ],
)
def test_api_items_retrieve_authenticated_related_team_administrators(
    teams, roles, mock_user_teams
):
    """
    Authenticated users should be allowed to retrieve an item to which they
    are related via a team whatever the role.
    """
    mock_user_teams.return_value = teams

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted")

    factories.TeamItemAccessFactory(item=item, team="readers", role="reader")
    factories.TeamItemAccessFactory(item=item, team="editors", role="editor")
    factories.TeamItemAccessFactory(
        item=item, team="administrators", role="administrator"
    )
    factories.TeamItemAccessFactory(item=item, team="owners", role="owner")
    factories.TeamItemAccessFactory(item=item)
    factories.TeamItemAccessFactory()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    # pylint: disable=R0801
    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": item.get_abilities(user),
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 1,
        "is_favorite": False,
        "link_reach": "restricted",
        "link_role": item.link_role,
        "nb_accesses": 5,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": roles,
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


@pytest.mark.parametrize(
    "teams,roles",
    [
        [["owners"], ["owner"]],
        [["owners", "administrators"], ["owner", "administrator"]],
        [["members", "administrators", "owners"], ["owner", "administrator"]],
        [["unknown", "owners"], ["owner"]],
    ],
)
def test_api_items_retrieve_authenticated_related_team_owners(
    teams, roles, mock_user_teams
):
    """
    Authenticated users should be allowed to retrieve a restricted item to which
    they are related via a team whatever the role.
    """
    mock_user_teams.return_value = teams

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach="restricted")

    factories.TeamItemAccessFactory(item=item, team="readers", role="reader")
    factories.TeamItemAccessFactory(item=item, team="editors", role="editor")
    factories.TeamItemAccessFactory(
        item=item, team="administrators", role="administrator"
    )
    factories.TeamItemAccessFactory(item=item, team="owners", role="owner")
    factories.TeamItemAccessFactory(item=item)
    factories.TeamItemAccessFactory()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    # pylint: disable=R0801
    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": item.get_abilities(user),
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 1,
        "is_favorite": False,
        "link_reach": "restricted",
        "link_role": item.link_role,
        "nb_accesses": 5,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": roles,
        "type": item.type,
        "upload_state": models.ItemUploadStateChoices.PENDING
        if item.type == models.ItemTypeChoices.FILE
        else None,
        "url": None,
        "mimetype": None,
        "main_workspace": False,
        "filename": item.filename,
        "size": None,
        "description": None,
    }


def test_api_items_retrieve_user_roles(django_assert_num_queries):
    """
    Roles should be annotated on querysets taking into account all items ancestors.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    grand_parent = factories.ItemFactory(
        users=factories.UserFactory.create_batch(2), type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        users=factories.UserFactory.create_batch(2),
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        parent=parent,
        type=models.ItemTypeChoices.FILE,
        users=factories.UserFactory.create_batch(2),
    )

    accesses = (
        factories.UserItemAccessFactory(item=grand_parent, user=user),
        factories.UserItemAccessFactory(item=parent, user=user),
        factories.UserItemAccessFactory(item=item, user=user),
    )
    expected_roles = {access.role for access in accesses}

    with django_assert_num_queries(11):
        response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200

    user_roles = response.json()["user_roles"]
    assert set(user_roles) == expected_roles


def test_api_items_retrieve_numqueries_with_link_trace(django_assert_num_queries):
    """If the link traced already exists, the number of queries should be minimal."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        users=[user], link_traces=[user], type=models.ItemTypeChoices.FILE
    )

    with django_assert_num_queries(4):
        response = client.get(f"/api/v1.0/items/{item.id!s}/")

    with django_assert_num_queries(3):
        response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200

    assert response.json()["id"] == str(item.id)


# Soft/permanent delete


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_retrieve_soft_deleted_anonymous(reach, depth):
    """
    A soft/permanently deleted public item should not be accessible via its
    detail endpoint for anonymous users, and should return a 404.
    """
    user = factories.UserFactory()
    items = []
    for i in range(depth):
        items.append(
            factories.ItemFactory(
                link_reach=reach, type=models.ItemTypeChoices.FOLDER, creator=user
            )
            if i == 0
            else factories.ItemFactory(
                parent=items[-1], type=models.ItemTypeChoices.FOLDER, creator=user
            )
        )
    assert models.Item.objects.count() == depth + 1  # +1 for the main workspace

    response = APIClient().get(f"/api/v1.0/items/{items[-1].id!s}/")

    assert response.status_code == 200 if reach == "public" else 401

    # Delete any one of the items...
    deleted_item = random.choice(items)
    deleted_item.soft_delete()

    response = APIClient().get(f"/api/v1.0/items/{items[-1].id!s}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}

    fourty_days_ago = timezone.now() - timedelta(days=40)
    deleted_item.deleted_at = fourty_days_ago
    deleted_item.ancestors_deleted_at = fourty_days_ago
    deleted_item.save()

    response = APIClient().get(f"/api/v1.0/items/{items[-1].id!s}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize("reach", models.LinkReachChoices.values)
def test_api_items_retrieve_soft_deleted_authenticated(reach, depth):
    """
    A soft/permanently deleted item should not be accessible via its detail endpoint for
    authenticated users not related to the item.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    items = []
    for i in range(depth):
        items.append(
            factories.ItemFactory(
                link_reach=reach, type=models.ItemTypeChoices.FOLDER, creator=user
            )
            if i == 0
            else factories.ItemFactory(
                parent=items[-1], type=models.ItemTypeChoices.FOLDER, creator=user
            )
        )
    assert models.Item.objects.count() == depth + 1  # +1 for the main workspace

    response = client.get(f"/api/v1.0/items/{items[-1].id!s}/")

    assert response.status_code == 200 if reach in ["public", "authenticated"] else 403

    # Delete any one of the items...
    deleted_item = random.choice(items)
    deleted_item.soft_delete()

    response = client.get(f"/api/v1.0/items/{items[-1].id!s}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}

    fourty_days_ago = timezone.now() - timedelta(days=40)
    deleted_item.deleted_at = fourty_days_ago
    deleted_item.ancestors_deleted_at = fourty_days_ago
    deleted_item.save()

    response = client.get(f"/api/v1.0/items/{items[-1].id!s}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize("role", models.RoleChoices.values)
def test_api_items_retrieve_soft_deleted_related(role, depth):
    """
    A soft deleted item should only be accessible via its detail endpoint by
    users with specific "owner" access rights.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    items = []
    for i in range(depth):
        items.append(
            factories.UserItemAccessFactory(
                role=role,
                user=user,
                item__type=models.ItemTypeChoices.FOLDER,
                item__creator=user,
            ).item
            if i == 0
            else factories.ItemFactory(
                parent=items[-1], type=models.ItemTypeChoices.FOLDER, creator=user
            )
        )
    assert models.Item.objects.count() == depth + 1  # +1 for the main workspace
    item = items[-1]

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200

    # Delete any one of the items
    deleted_item = random.choice(items)
    deleted_item.soft_delete()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    if role == "owner":
        assert response.status_code == 200
        assert response.json()["id"] == str(item.id)
    else:
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found."}


@pytest.mark.parametrize("depth", [1, 2, 3])
@pytest.mark.parametrize("role", models.RoleChoices.values)
def test_api_items_retrieve_permanently_deleted_related(role, depth):
    """
    A permanently deleted item should not be accessible via its detail endpoint for
    authenticated users with specific access rights whatever their role.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    items = []
    for i in range(depth):
        items.append(
            factories.UserItemAccessFactory(
                role=role,
                user=user,
                item__type=models.ItemTypeChoices.FOLDER,
                item__creator=user,
            ).item
            if i == 0
            else factories.ItemFactory(
                parent=items[-1], type=models.ItemTypeChoices.FOLDER, creator=user
            )
        )
    assert models.Item.objects.count() == depth + 1  # +1 for the main workspace
    item = items[-1]

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200

    # Delete any one of the items
    deleted_item = random.choice(items)
    fourty_days_ago = timezone.now() - timedelta(days=40)
    with mock.patch("django.utils.timezone.now", return_value=fourty_days_ago):
        deleted_item.soft_delete()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


def test_api_items_retrieve_file_uploaded():
    """
    The `url` property should not be none if the item is a file and has been uploaded.
    """

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FILE, link_reach="public")
    item.upload_state = models.ItemUploadStateChoices.UPLOADED
    item.filename = "logo.png"
    item.mimetype = "image/png"
    item.size = 8
    item.save()

    response = client.get(f"/api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(item.id),
        "abilities": item.get_abilities(user),
        "created_at": item.created_at.isoformat().replace("+00:00", "Z"),
        "creator": {
            "full_name": item.creator.full_name,
            "short_name": item.creator.short_name,
        },
        "depth": 1,
        "is_favorite": False,
        "link_reach": "public",
        "link_role": item.link_role,
        "nb_accesses": 0,
        "numchild": 0,
        "numchild_folder": 0,
        "path": str(item.path),
        "title": item.title,
        "updated_at": item.updated_at.isoformat().replace("+00:00", "Z"),
        "user_roles": [],
        "type": models.ItemTypeChoices.FILE,
        "upload_state": models.ItemUploadStateChoices.UPLOADED,
        "url": f"http://localhost:8083/media/item/{item.id!s}/logo.png",
        "mimetype": "image/png",
        "main_workspace": False,
        "filename": item.filename,
        "size": 8,
        "description": None,
    }
