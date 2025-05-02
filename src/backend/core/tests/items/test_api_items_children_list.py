"""
Tests for items API endpoint in drive's core app: retrieve
"""

import random

from django.contrib.auth.models import AnonymousUser

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def test_api_items_children_list_anonymous_public_standalone():
    """Anonymous users should be allowed to retrieve the children of a public item."""
    item = factories.ItemFactory(
        link_reach="public", type=models.ItemTypeChoices.FOLDER
    )
    child1, child2 = factories.ItemFactory.create_batch(2, parent=item)
    factories.UserItemAccessFactory(item=child1)

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/children/")

    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(AnonymousUser()),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 2,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(AnonymousUser()),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 2,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 0,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


def test_api_items_children_list_anonymous_public_parent():
    """
    Anonymous users should be allowed to retrieve the children of an item who
    has a public ancestor.
    """
    grand_parent = factories.ItemFactory(
        link_reach="public", type=models.ItemTypeChoices.FOLDER
    )
    parent = factories.ItemFactory(
        parent=grand_parent,
        link_reach=random.choice(["authenticated", "restricted"]),
        type=models.ItemTypeChoices.FOLDER,
    )
    item = factories.ItemFactory(
        link_reach=random.choice(["authenticated", "restricted"]),
        parent=parent,
        type=models.ItemTypeChoices.FOLDER,
    )
    child1, child2 = factories.ItemFactory.create_batch(
        2, parent=item, type=models.ItemTypeChoices.FILE
    )
    factories.UserItemAccessFactory(item=child1)

    child2.upload_state = models.ItemUploadStateChoices.UPLOADED
    child2.filename = "logo.png"
    child2.save()

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/children/")

    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(AnonymousUser()),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 4,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": models.ItemTypeChoices.FILE,
                "upload_state": models.ItemUploadStateChoices.PENDING,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(AnonymousUser()),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 4,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 0,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": models.ItemTypeChoices.FILE,
                "upload_state": models.ItemUploadStateChoices.UPLOADED,
                "url": f"http://localhost:8083/media/item/{child2.id!s}/logo.png",
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


@pytest.mark.parametrize("reach", ["restricted", "authenticated"])
def test_api_items_children_list_anonymous_restricted_or_authenticated(reach):
    """
    Anonymous users should not be able to retrieve children of an item that is not public.
    """
    item = factories.ItemFactory(link_reach=reach, type=models.ItemTypeChoices.FOLDER)
    factories.ItemFactory.create_batch(2, parent=item)

    response = APIClient().get(f"/api/v1.0/items/{item.id!s}/children/")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_children_list_authenticated_unrelated_public_or_authenticated(
    reach,
):
    """
    Authenticated users should be able to retrieve the children of a public/authenticated
    item to which they are not related.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=reach, type=models.ItemTypeChoices.FOLDER)
    child1, child2 = factories.ItemFactory.create_batch(2, parent=item)
    factories.UserItemAccessFactory(item=child1)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(user),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 2,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(user),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 2,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 0,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


@pytest.mark.parametrize("reach", ["public", "authenticated"])
def test_api_items_children_list_authenticated_public_or_authenticated_parent(
    reach,
):
    """
    Authenticated users should be allowed to retrieve the children of an item who
    has a public or authenticated ancestor.
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
    item = factories.ItemFactory(
        link_reach="restricted", parent=parent, type=models.ItemTypeChoices.FOLDER
    )
    child1, child2 = factories.ItemFactory.create_batch(2, parent=item)
    factories.UserItemAccessFactory(item=child1)

    response = client.get(f"/api/v1.0/items/{item.id!s}/children/")

    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(user),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 4,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(user),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 4,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 0,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


def test_api_items_children_list_authenticated_unrelated_restricted():
    """
    Authenticated users should not be allowed to retrieve the children of a item that is
    restricted and to which they are not related.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    child1, _child2 = factories.ItemFactory.create_batch(2, parent=item)
    factories.UserItemAccessFactory(item=child1)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/",
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_api_items_children_list_authenticated_related_direct():
    """
    Authenticated users should be allowed to retrieve the children of a item
    to which they are directly related whatever the role.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    access = factories.UserItemAccessFactory(item=item, user=user)
    factories.UserItemAccessFactory(item=item)

    child1, child2 = factories.ItemFactory.create_batch(2, parent=item)
    factories.UserItemAccessFactory(item=child1)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(user),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 2,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 3,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [access.role],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(user),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 2,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 2,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [access.role],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


def test_api_items_children_list_authenticated_related_parent():
    """
    Authenticated users should be allowed to retrieve the children of a item if they
    are related to one of its ancestors whatever the role.
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
    item = factories.ItemFactory(
        parent=parent, link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )

    child1, child2 = factories.ItemFactory.create_batch(2, parent=item)
    factories.UserItemAccessFactory(item=child1)

    grand_parent_access = factories.UserItemAccessFactory(item=grand_parent, user=user)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(user),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 4,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 2,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [grand_parent_access.role],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(user),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 4,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [grand_parent_access.role],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


def test_api_items_children_list_authenticated_related_child():
    """
    Authenticated users should not be allowed to retrieve all the children of an item
    as a result of being related to one of its children.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    child1, _child2 = factories.ItemFactory.create_batch(2, parent=item)

    factories.UserItemAccessFactory(item=child1, user=user)
    factories.UserItemAccessFactory(item=item)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/",
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_api_items_children_list_authenticated_related_team_none(mock_user_teams):
    """
    Authenticated users should not be able to retrieve the children of a restricted item
    related to teams in which the user is not.
    """
    mock_user_teams.return_value = []

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    factories.ItemFactory.create_batch(2, parent=item)

    factories.TeamItemAccessFactory(item=item, team="myteam")

    response = client.get(f"/api/v1.0/items/{item.id!s}/children/")
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_api_items_children_list_authenticated_related_team_members(
    mock_user_teams,
):
    """
    Authenticated users should be allowed to retrieve the children of an item to which they
    are related via a team whatever the role.
    """
    mock_user_teams.return_value = ["myteam"]

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
    child1, child2 = factories.ItemFactory.create_batch(2, parent=item)

    access = factories.TeamItemAccessFactory(item=item, team="myteam")

    response = client.get(f"/api/v1.0/items/{item.id!s}/children/")

    # pylint: disable=R0801
    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(user),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 2,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [access.role],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
            {
                "abilities": child2.get_abilities(user),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 2,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 1,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [access.role],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


def test_api_items_children_list_filter_type():
    """
    Authenticated users should be allowed to retrieve the children of an item
    to which they are directly related whatever the role and filter by type.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    access = factories.UserItemAccessFactory(item=item, user=user)
    factories.UserItemAccessFactory(item=item)

    child1 = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=child1)

    child2 = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=child2)

    # filter by type: folder
    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/?type=folder",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child1.get_abilities(user),
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child1.creator.full_name,
                    "short_name": child1.creator.short_name,
                },
                "depth": 2,
                "id": str(child1.id),
                "is_favorite": False,
                "link_reach": child1.link_reach,
                "link_role": child1.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 3,
                "path": str(child1.path),
                "title": child1.title,
                "updated_at": child1.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [access.role],
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }

    # filter by type: file
    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/?type=file",
    )
    assert response.status_code == 200
    assert response.json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "abilities": child2.get_abilities(user),
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "full_name": child2.creator.full_name,
                    "short_name": child2.creator.short_name,
                },
                "depth": 2,
                "id": str(child2.id),
                "is_favorite": False,
                "link_reach": child2.link_reach,
                "link_role": child2.link_role,
                "numchild": 0,
                "numchild_folder": 0,
                "nb_accesses": 3,
                "path": str(child2.path),
                "title": child2.title,
                "updated_at": child2.updated_at.isoformat().replace("+00:00", "Z"),
                "user_roles": [access.role],
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
            },
        ],
    }


def test_api_items_children_list_filter_wrong_type():
    """
    Filtering with a wront type should not filter result
    """

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=item, user=user)
    factories.UserItemAccessFactory(item=item)

    child1 = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FOLDER)
    factories.UserItemAccessFactory(item=child1)

    child2 = factories.ItemFactory(parent=item, type=models.ItemTypeChoices.FILE)
    factories.UserItemAccessFactory(item=child2)

    response = client.get(
        f"/api/v1.0/items/{item.id!s}/children/?type=unknown",
    )
    assert response.status_code == 400

    assert response.json() == {
        "type": ["Select a valid choice. unknown is not one of the available choices."]
    }
