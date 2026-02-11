"""
Tests for the Resource Server API for items.

Not testing external API endpoints that are already tested in the /api
because the resource server viewsets inherit from the api viewsets.

"""

from datetime import timedelta
from io import BytesIO

from django.conf import settings as django_settings
from django.core.files.storage import default_storage
from django.test import override_settings
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.tests.utils.urls import reload_urls

pytestmark = pytest.mark.django_db

# pylint: disable=too-many-lines
# pylint: disable=unused-argument


def test_api_items_retrieve_anonymous_public_standalone():
    """
    Anonymous users should not be allowed to retrieve an item from external
    API if resource server is not enabled.
    """
    item = factories.ItemFactory(link_reach="public")

    response = APIClient().get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 404


def test_api_items_list_connected_not_resource_server():
    """
    Connected users should not be allowed to list items if resource server is not enabled.
    """
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(item=item, user=user, role="reader")

    response = client.get("/external_api/v1.0/items/")

    assert response.status_code == 404


def test_api_items_list_connected_resource_server(
    user_token, resource_server_backend, user_specific_sub
):
    """Connected users should be allowed to list items from a resource server."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(item=item, user=user_specific_sub, role="reader")

    response = client.get("/external_api/v1.0/items/")

    assert response.status_code == 200


def test_api_items_routes_not_exposed_when_items_disabled(
    user_token, resource_server_backend_conf
):
    """Items routes should be 404 when the items resource is not enabled."""
    django_settings.EXTERNAL_API = {
        "items": {"enabled": False, "actions": []},
        "item_access": {"enabled": False, "actions": []},
        "item_invitation": {"enabled": False, "actions": []},
        "users": {"enabled": True, "actions": ["get_me"]},
    }
    reload_urls()

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get("/external_api/v1.0/items/")
    assert response.status_code == 404


def test_api_items_list_connected_resource_server_with_invalid_token(
    user_token, resource_server_backend
):
    """User with an invalid sub should not be allowed to retrieve items from a resource server."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get("/external_api/v1.0/items/")

    assert response.status_code == 401


def test_api_items_retrieve_connected_resource_server_with_wrong_abilities(
    user_token, user_specific_sub, resource_server_backend
):
    """
    User with wrong abilities should not be allowed to retrieve an item from
    a resource server.
    """

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


def test_api_items_retrieve_connected_resource_server_using_access_token(
    user_token, resource_server_backend, user_specific_sub
):
    """
    User with an access token should be allowed to retrieve an item from a resource server.
    """

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.LinkRoleChoices.READER
    )

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 200


def test_api_items_upload_resource_server_using_access_token(
    user_token, resource_server_backend, user_specific_sub
):
    """
    User with an access token should be allowed to upload an item to a resource server.
    """

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/children/",
        {
            "type": models.ItemTypeChoices.FILE,
            "filename": "file.txt",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == models.ItemTypeChoices.FILE
    assert data["filename"] == "file.txt"
    assert "policy" in data
    child = models.Item.objects.get(id=data["id"])

    default_storage.save(
        child.file_key,
        BytesIO(b"my prose"),
    )

    response = client.post(f"/external_api/v1.0/items/{child.id!s}/upload-ended/")

    assert response.status_code == 200


# Non allowed actions on resource server.


def test_api_items_delete_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should notbe allowed to delete an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.delete(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended", "destroy"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_delete_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to delete an item from a resource server
    when the destroy action is enabled in EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.delete(f"/external_api/v1.0/items/{item.id!s}/")

    assert response.status_code == 204
    # Verify the item is soft deleted
    item.refresh_from_db()
    assert item.deleted_at is not None


def test_api_items_hard_delete_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should notbe allowed to hard delete an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.delete(f"/external_api/v1.0/items/{item.id!s}/hard-delete/")

    assert response.status_code == 403


def test_api_items_patch_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should notbe allowed to patch an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.patch(
        f"/external_api/v1.0/items/{item.id!s}/", {"title": "new title"}
    )

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": [
                "list",
                "retrieve",
                "children",
                "upload_ended",
                "partial_update",
            ],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_patch_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to patch an item from a resource server
    when the partial_update action is enabled in EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    original_title = item.title
    response = client.patch(
        f"/external_api/v1.0/items/{item.id!s}/", {"title": "new title"}
    )

    assert response.status_code == 200
    # Verify the item is updated
    item.refresh_from_db()
    assert item.title == "new title"
    assert item.title != original_title


def test_api_items_put_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to put an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.put(
        f"/external_api/v1.0/items/{item.id!s}/", {"title": "new title"}
    )

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended", "update"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_put_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to put (update) an item from a resource server
    when the update action is enabled in EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    original_title = item.title
    response = client.put(
        f"/external_api/v1.0/items/{item.id!s}/", {"title": "new title"}
    )

    assert response.status_code == 200
    # Verify the item is updated
    item.refresh_from_db()
    assert item.title == "new title"
    assert item.title != original_title


def test_api_items_move_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to move an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/move/",
        {
            "target_item_id": factories.ItemFactory(
                link_reach=models.LinkReachChoices.RESTRICTED
            ).id
        },
    )

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended", "move"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_move_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to move an item from a resource server
    when the move action is enabled in EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item_parent = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        item=item_parent, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED, parent=item_parent
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    target = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        item=target, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    original_path = item.path
    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/move/",
        {"target_item_id": str(target.id)},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "item moved successfully."}
    # Verify the item is moved
    item.refresh_from_db()
    assert item.path != original_path
    assert str(target.id) in item.path


def test_api_items_restore_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to restore an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.post(f"/external_api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended", "restore"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_restore_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to restore an item from a resource server
    when the restore action is enabled in EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    # Create a soft-deleted item
    now = timezone.now() - timedelta(days=15)
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED, deleted_at=now
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.post(f"/external_api/v1.0/items/{item.id!s}/restore/")

    assert response.status_code == 200
    assert response.json() == {"detail": "item has been successfully restored."}
    # Verify the item is restored
    item.refresh_from_db()
    assert item.deleted_at is None
    assert item.ancestors_deleted_at is None


def test_api_items_trashbin_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should notbe allowed to list the trashbin from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.get("/external_api/v1.0/items/trashbin/")

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended", "trashbin"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_trashbin_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to list the trashbin from a resource server
    when the trashbin action is enabled in EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    # Create a soft-deleted item owned by the user
    now = timezone.now() - timedelta(days=15)
    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED, deleted_at=now
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.get("/external_api/v1.0/items/trashbin/")

    assert response.status_code == 200
    content = response.json()
    assert "results" in content
    assert "count" in content
    # Verify the deleted item is in the results
    assert content["count"] >= 1
    item_ids = [result["id"] for result in content["results"]]
    assert str(item.id) in item_ids


def test_api_items_link_configuration_resource_server_not_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to update the link configuration
    of an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.put(
        f"/external_api/v1.0/items/{item.id!s}/link-configuration/",
        {
            "link_reach": models.LinkReachChoices.RESTRICTED,
            "link_role": models.LinkRoleChoices.READER,
        },
    )

    assert response.status_code == 403


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": [
                "list",
                "retrieve",
                "children",
                "upload_ended",
                "link_configuration",
            ],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_link_configuration_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to update the link configuration of an item
    from a resource server when the link_configuration action is enabled in
    EXTERNAL_API settings.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        link_role=models.LinkRoleChoices.READER,
    )
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.put(
        f"/external_api/v1.0/items/{item.id!s}/link-configuration/",
        {
            "link_reach": models.LinkReachChoices.PUBLIC,
            "link_role": models.LinkRoleChoices.EDITOR,
        },
    )

    assert response.status_code == 200
    # Verify the item's link configuration is updated
    item.refresh_from_db()
    assert item.link_reach == models.LinkReachChoices.PUBLIC
    assert item.link_role == models.LinkRoleChoices.EDITOR


def test_api_items_accesses_resource_server_not_allowed(
    user_token, resource_server_backend_conf, user_specific_sub
):
    """
    Connected users should not be allowed to list the accesses of
    an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 404


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended"],
        },
        "item_access": {
            "enabled": True,
            "actions": ["list"],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_accesses_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to list the accesses of an item from a resource server
    when the list action is enabled in EXTERNAL_API item_access settings.
    """

    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    user_access = factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )
    # Create additional accesses
    other_access = factories.UserItemAccessFactory(
        item=item, role=models.RoleChoices.READER
    )

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/accesses/")

    assert response.status_code == 200
    content = response.json()
    # Verify the accesses are in the results
    assert len(content) >= 2
    access_ids = [result["id"] for result in content]
    assert str(user_access.id) in access_ids
    assert str(other_access.id) in access_ids


def test_api_items_accesses_create_resource_server_not_allowed(
    user_token, resource_server_backend_conf, user_specific_sub
):
    """
    Connected users should not be allowed to create an access for an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        {"user_id": factories.UserFactory().id, "role": models.RoleChoices.READER},
    )

    assert response.status_code == 404


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended"],
        },
        "item_access": {
            "enabled": True,
            "actions": ["list", "create"],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_accesses_create_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to create an access for an item from a resource server
    when the create action is enabled in EXTERNAL_API item_access settings.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    other_user = factories.UserFactory()
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 0

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/accesses/",
        {"user_id": str(other_user.id), "role": models.RoleChoices.READER},
        format="json",
    )

    assert response.status_code == 201
    # Verify the access was created
    assert models.ItemAccess.objects.filter(user=other_user, item=item).count() == 1
    new_access = models.ItemAccess.objects.filter(user=other_user, item=item).get()
    assert new_access.role == models.RoleChoices.READER
    # Verify the response contains the created access
    response_data = response.json()
    assert response_data["id"] == str(new_access.id)
    assert response_data["role"] == models.RoleChoices.READER


def test_api_items_accesses_delete_resource_server_not_allowed(
    user_token, resource_server_backend_conf, user_specific_sub
):
    """
    Connected users should not be allowed to create an access for an item from a resource server.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    other_user = factories.UserFactory()
    access = factories.UserItemAccessFactory(
        item=item, user=other_user, role=models.RoleChoices.READER
    )

    count_before = models.ItemAccess.objects.count()
    response = client.delete(
        f"/external_api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
    )
    assert response.status_code == 404
    assert models.ItemAccess.objects.count() == count_before


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended"],
        },
        "item_access": {
            "enabled": True,
            "actions": ["list", "create", "destroy"],
        },
        "item_invitation": {
            "enabled": False,
            "actions": [],
        },
    }
)
def test_api_items_accesses_delete_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should not be allowed to create an access for an item from a resource server.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    other_user = factories.UserFactory()
    access = factories.UserItemAccessFactory(
        item=item, user=other_user, role=models.RoleChoices.READER
    )

    count_before = models.ItemAccess.objects.count()
    response = client.delete(
        f"/external_api/v1.0/items/{access.item_id!s}/accesses/{access.id!s}/",
    )
    assert response.status_code == 204
    assert models.ItemAccess.objects.count() == count_before - 1


def test_api_items_invitations_resource_server_not_allowed(
    user_token, resource_server_backend_conf, user_specific_sub
):
    """
    Connected users should not be allowed to list the invitations of an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/invitations/")

    assert response.status_code == 404


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": True,
            "actions": ["list"],
        },
    }
)
def test_api_items_invitations_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to list the invitations of an item from a resource server
    when the list action is enabled in EXTERNAL_API item_invitation settings.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    # Create invitations
    invitation = factories.InvitationFactory(item=item, issuer=user_specific_sub)
    other_invitation = factories.InvitationFactory(item=item)

    response = client.get(f"/external_api/v1.0/items/{item.id!s}/invitations/")

    assert response.status_code == 200
    content = response.json()
    assert "results" in content
    assert "count" in content
    # Verify the invitations are in the results
    assert content["count"] >= 2
    invitation_ids = [result["id"] for result in content["results"]]
    assert str(invitation.id) in invitation_ids
    assert str(other_invitation.id) in invitation_ids


def test_api_items_invitations_create_resource_server_not_allowed(
    user_token, resource_server_backend_conf, user_specific_sub
):
    """
    Connected users should not be allowed to create an invitation for an
    item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/invitations/",
        {"email": "test@example.com", "role": models.RoleChoices.READER},
    )

    assert response.status_code == 404


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": True,
            "actions": ["list", "create"],
        },
    }
)
def test_api_items_invitations_create_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to create an invitation for an item from a resource server
    when the create action is enabled in EXTERNAL_API item_invitation settings.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    assert (
        models.Invitation.objects.filter(item=item, email="test@example.com").count()
        == 0
    )

    response = client.post(
        f"/external_api/v1.0/items/{item.id!s}/invitations/",
        {"email": "test@example.com", "role": models.RoleChoices.READER},
        format="json",
    )

    assert response.status_code == 201
    # Verify the invitation was created
    assert (
        models.Invitation.objects.filter(item=item, email="test@example.com").count()
        == 1
    )
    new_invitation = models.Invitation.objects.filter(
        item=item, email="test@example.com"
    ).get()
    assert new_invitation.role == models.RoleChoices.READER
    assert new_invitation.issuer == user_specific_sub
    # Verify the response contains the created invitation
    response_data = response.json()
    assert response_data["id"] == str(new_invitation.id)
    assert response_data["email"] == "test@example.com"
    assert response_data["role"] == models.RoleChoices.READER


def test_api_items_invitations_delete_resource_server_not_allowed(
    user_token, resource_server_backend_conf, user_specific_sub
):
    """
    Connected users should not be allowed to delete an invitation for
    an item from a resource server.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    other_user = factories.UserFactory()
    invitation = factories.InvitationFactory(item=item, issuer=other_user)

    count_before = models.Invitation.objects.count()
    response = client.delete(
        f"/external_api/v1.0/items/{invitation.item_id!s}/invitations/{invitation.id!s}/",
    )
    assert response.status_code == 404
    assert models.Invitation.objects.count() == count_before


@override_settings(
    EXTERNAL_API={
        "items": {
            "enabled": True,
            "actions": ["list", "retrieve", "children", "upload_ended"],
        },
        "item_access": {
            "enabled": False,
            "actions": [],
        },
        "item_invitation": {
            "enabled": True,
            "actions": ["list", "create", "destroy"],
        },
    }
)
def test_api_items_invitations_delete_resource_server_allowed(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Connected users should be allowed to create an invitation for an item from a resource server
    when the create action is enabled in EXTERNAL_API item_invitation settings.
    """
    reload_urls()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    item = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    factories.UserItemAccessFactory(
        item=item, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    other_user = factories.UserFactory()
    invitation = factories.InvitationFactory(item=item, issuer=other_user)

    count_before = models.Invitation.objects.count()
    response = client.delete(
        f"/external_api/v1.0/items/{invitation.item_id!s}/invitations/{invitation.id!s}/",
    )
    assert response.status_code == 204
    assert models.Invitation.objects.count() == count_before - 1
