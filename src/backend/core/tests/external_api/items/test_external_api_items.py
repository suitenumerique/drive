"""
Tests for the Resource Server API for items.

Not testing external API endpoints that are already tested in the /api
because the resource server viewsets inherit from the api viewsets.

"""

from io import BytesIO

from django.core.files.storage import default_storage

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

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
