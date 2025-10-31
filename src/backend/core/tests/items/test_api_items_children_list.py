"""
Tests for items API endpoint in drive's core app: retrieve
"""

import random

from django.contrib.auth.models import AnonymousUser

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

# pylint: disable=too-many-lines


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
                "ancestors_link_reach": "public",
                "ancestors_link_role": item.link_role,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": None,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(AnonymousUser()),
                "ancestors_link_reach": "public",
                "ancestors_link_role": item.link_role,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": None,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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

    child2.upload_state = models.ItemUploadStateChoices.READY
    child2.filename = "logo.png"
    child2.mimetype = "image/png"
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
                "ancestors_link_reach": "public",
                "ancestors_link_role": grand_parent.link_role,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": None,
                "type": models.ItemTypeChoices.FILE,
                "upload_state": models.ItemUploadStateChoices.PENDING,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(AnonymousUser()),
                "ancestors_link_reach": "public",
                "ancestors_link_role": grand_parent.link_role,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": None,
                "type": models.ItemTypeChoices.FILE,
                "upload_state": models.ItemUploadStateChoices.READY,
                "url": f"http://localhost:8083/media/item/{child2.id!s}/logo.png",
                "url_preview": f"http://localhost:8083/media/preview/item/{child2.id!s}/logo.png",
                "mimetype": "image/png",
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
        "errors": [
            {
                "attr": None,
                "code": "not_authenticated",
                "detail": "Authentication credentials were not provided.",
            },
        ],
        "type": "client_error",
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
                "ancestors_link_reach": reach,
                "ancestors_link_role": item.link_role,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": None,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(user),
                "ancestors_link_reach": reach,
                "ancestors_link_role": item.link_role,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": None,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
                "ancestors_link_reach": reach,
                "ancestors_link_role": grand_parent.link_role,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": None,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(user),
                "ancestors_link_reach": reach,
                "ancestors_link_role": grand_parent.link_role,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": None,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
    }


def test_api_items_children_list_authenticated_related_direct():
    """
    Authenticated users should be allowed to retrieve the children of an item
    to which they are directly related whatever the role.
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
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
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": access.role,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(user),
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": access.role,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": grand_parent_access.role,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(user),
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": grand_parent_access.role,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
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
        "errors": [
            {
                "attr": None,
                "code": "permission_denied",
                "detail": "You do not have permission to perform this action.",
            },
        ],
        "type": "client_error",
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
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": access.role,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
            },
            {
                "abilities": child2.get_abilities(user),
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": access.role,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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

    item = factories.ItemFactory(
        link_reach="restricted", type=models.ItemTypeChoices.FOLDER
    )
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
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child1.computed_link_reach,
                "computed_link_role": child1.computed_link_role,
                "created_at": child1.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child1.creator.id),
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
                "user_role": access.role,
                "type": child1.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child1.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child1.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
                "ancestors_link_reach": "restricted",
                "ancestors_link_role": None,
                "computed_link_reach": child2.computed_link_reach,
                "computed_link_role": child2.computed_link_role,
                "created_at": child2.created_at.isoformat().replace("+00:00", "Z"),
                "creator": {
                    "id": str(child2.creator.id),
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
                "user_role": access.role,
                "type": child2.type,
                "upload_state": models.ItemUploadStateChoices.PENDING
                if child2.type == models.ItemTypeChoices.FILE
                else None,
                "url": None,
                "url_preview": None,
                "mimetype": None,
                "main_workspace": False,
                "filename": child2.filename,
                "size": None,
                "description": None,
                "deleted_at": None,
                "hard_delete_at": None,
                "is_wopi_supported": False,
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
        "errors": [
            {
                "attr": "type",
                "code": "invalid",
                "detail": "Select a valid choice. unknown is not one of the available choices.",
            },
        ],
        "type": "validation_error",
    }


def test_api_items_children_list_with_suspicious_items():
    """
    Suspicious items should not be listed in children list for non creator.
    """
    creator = factories.UserFactory()
    other_user = factories.UserFactory()
    client = APIClient()
    client.force_login(other_user)

    parent_item = factories.ItemFactory(
        creator=creator,
        type=models.ItemTypeChoices.FOLDER,
        users=[creator, other_user],
    )

    # Create suspicious item as child
    suspicious_item = factories.ItemFactory(
        creator=creator,
        parent=parent_item,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        users=[creator, other_user],
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
    )

    # Create normal items as children
    normal_item1, normal_item2 = factories.ItemFactory.create_batch(
        2,
        creator=creator,
        parent=parent_item,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[creator, other_user],
        type=models.ItemTypeChoices.FILE,
        filename="normal.txt",
    )

    # Non-creator should not see suspicious item
    response = client.get(f"/api/v1.0/items/{parent_item.id!s}/children/")
    assert response.status_code == 200
    content = response.json()

    # Should only see 2 normal items, not the suspicious one
    assert content["count"] == 2
    item_ids = [item["id"] for item in content["results"]]
    assert str(suspicious_item.id) not in item_ids
    assert str(normal_item1.id) in item_ids
    assert str(normal_item2.id) in item_ids

    # Creator should see all items including suspicious one
    client.force_login(creator)
    response = client.get(f"/api/v1.0/items/{parent_item.id!s}/children/")
    assert response.status_code == 200
    content = response.json()

    # Should see all 3 items including suspicious one
    assert content["count"] == 3
    item_ids = [item["id"] for item in content["results"]]
    assert str(suspicious_item.id) in item_ids
    assert str(normal_item1.id) in item_ids
    assert str(normal_item2.id) in item_ids


def test_api_items_children_list_suspicious_item_should_not_work_for_anonymous():
    """
    Suspicious items should not be accessible via children endpoint for anonymous users.
    """
    creator = factories.UserFactory()

    parent_item = factories.ItemFactory(
        creator=creator,
        type=models.ItemTypeChoices.FOLDER,
        link_reach="public",
    )

    suspicious_item = factories.ItemFactory(
        creator=creator,
        parent=parent_item,
        update_upload_state=models.ItemUploadStateChoices.SUSPICIOUS,
        type=models.ItemTypeChoices.FILE,
        filename="suspicious.txt",
        link_reach="public",
    )

    # Anonymous user should not see suspicious item
    response = APIClient().get(f"/api/v1.0/items/{parent_item.id!s}/children/")
    assert response.status_code == 200
    content = response.json()

    # Should not see the suspicious item
    assert content["count"] == 0
    item_ids = [item["id"] for item in content["results"]]
    assert str(suspicious_item.id) not in item_ids
