"""
Tests for the items created through the external API with an exchanged token.

EXTERNAL_API_AUD_ITEM_ATTRIBUTES applies extra attributes to items created through
the external API, keyed by the audience of the resource server token. Menshen names
the service that exchanged the token in the introspection `client_id`, as RFC 7662
asks, by the audience id it is registered under, and Drive keys the setting on it: a
service keeps its attributes when it moves to token exchange. The audiences of the
token itself, which are Drive, are not what the setting is keyed on.

Menshen reports a token as active only while it still knows its source service, so an
active response always names one.
"""

import pytest
import responses
from rest_framework.test import APIClient

from core import factories, models
from core.tests.utils.menshen import (
    MENSHEN_INTROSPECTION_URL,
    MENSHEN_SOURCE,
    MENSHEN_TOKEN,
    menshen_introspection_response,
)

pytestmark = pytest.mark.django_db

# pylint: disable=unused-argument


def menshen_client(rsps, scope, source=MENSHEN_SOURCE):
    """Build an API client whose exchanged token carries the given scopes.

    `source` is the audience id of the service that exchanged the token, which Menshen
    reports as the introspection `client_id`.
    """
    rsps.add(
        responses.POST,
        MENSHEN_INTROSPECTION_URL,
        json=menshen_introspection_response(scope=scope, client_id=source),
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {MENSHEN_TOKEN}")

    return client


def test_api_items_create_root_menshen(menshen_backend_conf, user_specific_sub):
    """An exchanged token carrying the create scope should create a root item."""
    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:create").post(
            "/external_api/v1.0/items/",
            {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        )

    assert response.status_code == 201

    item = models.Item.objects.get(id=response.json()["id"])
    assert item.creator == user_specific_sub
    assert item.accesses.get(user=user_specific_sub).role == models.RoleChoices.OWNER


def test_api_items_create_root_menshen_applies_source_attributes(
    menshen_backend_conf, user_specific_sub
):
    """Items created with an exchanged token get the attributes of the calling service."""
    menshen_backend_conf.EXTERNAL_API_AUD_ITEM_ATTRIBUTES = {
        MENSHEN_SOURCE: {"quota_excluded": True}
    }

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:create").post(
            "/external_api/v1.0/items/",
            {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        )

    assert response.status_code == 201
    assert models.Item.objects.get(id=response.json()["id"]).quota_excluded is True


def test_api_items_create_children_menshen_applies_source_attributes(
    menshen_backend_conf, user_specific_sub
):
    """Children created with an exchanged token get those attributes too."""
    menshen_backend_conf.EXTERNAL_API_AUD_ITEM_ATTRIBUTES = {
        MENSHEN_SOURCE: {"quota_excluded": True}
    }

    parent = factories.ItemFactory(
        link_reach=models.LinkReachChoices.RESTRICTED,
        type=models.ItemTypeChoices.FOLDER,
    )
    factories.UserItemAccessFactory(
        item=parent, user=user_specific_sub, role=models.RoleChoices.OWNER
    )

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:create-children").post(
            f"/external_api/v1.0/items/{parent.id!s}/children/",
            {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        )

    assert response.status_code == 201
    assert models.Item.objects.get(id=response.json()["id"]).quota_excluded is True


def test_api_items_create_menshen_source_not_configured(menshen_backend_conf, user_specific_sub):
    """A service missing from the setting keeps the default item attributes."""
    menshen_backend_conf.EXTERNAL_API_AUD_ITEM_ATTRIBUTES = {
        MENSHEN_SOURCE: {"quota_excluded": True}
    }

    with responses.RequestsMock() as rsps:
        response = menshen_client(rsps, "drive:item:create", source="other_service").post(
            "/external_api/v1.0/items/",
            {"size": 8, "type": models.ItemTypeChoices.FILE, "filename": "file.txt"},
        )

    assert response.status_code == 201
    assert models.Item.objects.get(id=response.json()["id"]).quota_excluded is False
