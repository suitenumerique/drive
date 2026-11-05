"""
Tests for the `source` field on items created through the resource server API.
"""

from django.test import override_settings

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


def test_api_items_create_root_resource_server_source_is_client_id(
    user_token, resource_server_backend, user_specific_sub
):
    """
    Items created at the root through the external API carry the token client_id as
    source (the introspection mock reports client_id "some_service_provider").
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.post(
        "/external_api/v1.0/items/",
        {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
    )

    assert response.status_code == 201
    child = models.Item.objects.get(id=response.json()["id"])
    assert child.source == "some_service_provider"


def test_api_items_create_children_resource_server_source_is_client_id(
    user_token, resource_server_backend, user_specific_sub
):
    """Items created as children through the external API carry the token client_id as source."""
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
        {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
    )

    assert response.status_code == 201
    child = models.Item.objects.get(id=response.json()["id"])
    assert child.source == "some_service_provider"


@override_settings(
    EXTERNAL_API_AUD_ITEM_ATTRIBUTES={"some_service_provider": {"source": "custom_source"}}
)
def test_api_items_create_resource_server_aud_attributes_override_source(
    user_token, resource_server_backend, user_specific_sub
):
    """An explicit source in EXTERNAL_API_AUD_ITEM_ATTRIBUTES wins over the client_id."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

    response = client.post(
        "/external_api/v1.0/items/",
        {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
    )

    assert response.status_code == 201
    child = models.Item.objects.get(id=response.json()["id"])
    assert child.source == "custom_source"
