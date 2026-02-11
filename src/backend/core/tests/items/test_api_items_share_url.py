"""
Tests for share URL exposure on item detail responses.
"""

from django.test import override_settings

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.utils.share_links import compute_item_share_token

pytestmark = pytest.mark.django_db


@override_settings(DRIVE_PUBLIC_URL="https://drive.example.com")
def test_api_items_retrieve_share_url_exposed_for_owner_when_public():
    """Expose share_url for users allowed to configure sharing on public items."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.PUBLIC)
    factories.UserItemAccessFactory(item=item, user=user, role=models.RoleChoices.OWNER)

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.status_code == 200
    data = response.json()

    token = compute_item_share_token(item.id)
    assert data["share_url"] == f"https://drive.example.com/share/{token}"


@override_settings(DRIVE_PUBLIC_URL="https://drive.example.com")
def test_api_items_retrieve_share_url_not_exposed_without_link_configuration_ability():
    """Do not expose share_url when the user cannot configure link sharing."""
    user = factories.UserFactory()
    item = factories.ItemFactory(link_reach=models.LinkReachChoices.PUBLIC)
    factories.UserItemAccessFactory(
        item=item, user=user, role=models.RoleChoices.READER
    )

    client = APIClient()
    client.force_login(user)

    response = client.get(f"/api/v1.0/items/{item.id!s}/")
    assert response.status_code == 200
    data = response.json()

    assert "share_url" not in data
