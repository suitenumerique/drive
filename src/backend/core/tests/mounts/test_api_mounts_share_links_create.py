"""Tests for mount share link creation (virtual entries)."""

from django.test import override_settings

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db


def _make_static_mount(*, mount_id: str, share_enabled: bool) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "static",
        "enabled": True,
        "params": {
            "capabilities": {
                "mount.upload": False,
                "mount.preview": False,
                "mount.wopi": False,
                "mount.share_link": share_enabled,
            },
            "static_entries": [
                {"path": "/", "entry_type": "folder"},
                {"path": "/a", "entry_type": "folder"},
                {"path": "/a/b.txt", "entry_type": "file"},
            ],
        },
    }


def test_api_mounts_share_links_create_is_capability_gated(settings):
    """Share link creation rejects when mount.share_link is disabled."""
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(mount_id="alpha-mount", share_enabled=False)
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/mounts/alpha-mount/share-links/",
        data={"path": "/a/b.txt"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["errors"][0]["code"] == "mount.share_link.disabled"


@override_settings(DRIVE_PUBLIC_URL="https://drive.example.com")
def test_api_mounts_share_links_create_stores_token_and_returns_share_url(settings):
    """Creation stores a token mapping and returns a DRIVE_PUBLIC_URL-derived URL."""
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(mount_id="alpha-mount", share_enabled=True)
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.post(
        "/api/v1.0/mounts/alpha-mount/share-links/",
        data={"path": "////a/./b.txt"},
        format="json",
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["mount_id"] == "alpha-mount"
    assert payload["normalized_path"] == "/a/b.txt"
    assert payload["share_url"].startswith("https://drive.example.com/share/mount/")
    assert payload["token"]

    link = models.MountShareLink.objects.get(
        mount_id="alpha-mount", normalized_path="/a/b.txt"
    )
    assert link.token == payload["token"]


@override_settings(DRIVE_PUBLIC_URL="https://drive.example.com")
def test_api_mounts_share_links_create_is_idempotent(settings):
    """Repeated creation returns the same token for the same virtual entry."""
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(mount_id="alpha-mount", share_enabled=True)
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    r1 = client.post(
        "/api/v1.0/mounts/alpha-mount/share-links/",
        data={"path": "/a/b.txt"},
        format="json",
    )
    r2 = client.post(
        "/api/v1.0/mounts/alpha-mount/share-links/",
        data={"path": "/a/b.txt"},
        format="json",
    )

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["token"] == r2.json()["token"]
    assert (
        models.MountShareLink.objects.filter(
            mount_id="alpha-mount", normalized_path="/a/b.txt"
        ).count()
        == 1
    )
