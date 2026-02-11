"""
Tests for the token-enforced public share links browse endpoint.
"""

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.utils.share_links import compute_item_share_token

pytestmark = pytest.mark.django_db


def test_api_share_links_browse_root_folder_lists_children():
    """A public shared folder can be browsed without an authenticated session."""
    root = factories.ItemFactory(
        link_reach=models.LinkReachChoices.PUBLIC,
        type=models.ItemTypeChoices.FOLDER,
    )
    child = factories.ItemFactory(
        parent=root,
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )

    token = compute_item_share_token(root.id)
    response = APIClient().get(f"/api/v1.0/share-links/{token}/browse/")
    assert response.status_code == 200

    data = response.json()
    assert data["root_item_id"] == str(root.id)
    assert data["item"]["id"] == str(root.id)

    children = data["children"]
    assert children["count"] == 1
    assert children["results"][0]["id"] == str(child.id)
    assert "share_token=" in (children["results"][0]["url"] or "")


def test_api_share_links_browse_returns_404_when_not_public():
    """A valid token should still return 404 when sharing is not public."""
    root = factories.ItemFactory(link_reach=models.LinkReachChoices.RESTRICTED)
    token = compute_item_share_token(root.id)

    response = APIClient().get(f"/api/v1.0/share-links/{token}/browse/")
    assert response.status_code == 404


def test_api_share_links_browse_returns_404_for_invalid_token():
    """Invalid tokens must not leak whether an item exists."""
    response = APIClient().get("/api/v1.0/share-links/not-a-token/browse/")
    assert response.status_code == 404


def test_api_share_links_browse_rejects_item_outside_root_subtree():
    """Browsing outside the shared subtree returns a generic 404."""
    root = factories.ItemFactory(link_reach=models.LinkReachChoices.PUBLIC)
    outside = factories.ItemFactory(type=models.ItemTypeChoices.FOLDER)

    token = compute_item_share_token(root.id)
    response = APIClient().get(
        f"/api/v1.0/share-links/{token}/browse/?item_id={outside.id!s}"
    )
    assert response.status_code == 404
