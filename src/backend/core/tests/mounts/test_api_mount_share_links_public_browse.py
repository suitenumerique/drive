"""Tests for public MountProvider share links (unauthenticated browse)."""

import secrets

from django.test import override_settings

import pytest
from rest_framework.test import APIClient

from core import models

pytestmark = pytest.mark.django_db


def _make_static_mount(*, mount_id: str) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "static",
        "enabled": True,
        "params": {
            "capabilities": {"mount.share_link": True},
            "static_entries": [
                {"path": "/", "entry_type": "folder"},
                {"path": "/a", "entry_type": "folder"},
                {"path": "/a/b.txt", "entry_type": "file"},
            ],
        },
    }


def test_api_mount_share_links_browse_invalid_token_is_404(settings):
    """Unknown/invalid tokens are generic 404 (no-leak)."""
    settings.MOUNTS_REGISTRY = [_make_static_mount(mount_id="alpha-mount")]

    response = APIClient().get("/api/v1.0/mount-share-links/not-a-token/browse/")
    assert response.status_code == 404
    assert response.json()["errors"][0]["code"] == "mount.share_link.not_found"


def test_api_mount_share_links_browse_known_token_missing_mount_is_410(settings):
    """Known token with missing/disabled mount returns 410."""
    settings.MOUNTS_REGISTRY = []

    token = secrets.token_urlsafe(16)
    models.MountShareLink.objects.create(
        token=token,
        mount_id="alpha-mount",
        normalized_path="/a",
        created_by=None,
    )

    response = APIClient().get(f"/api/v1.0/mount-share-links/{token}/browse/")
    assert response.status_code == 410
    assert response.json()["errors"][0]["code"] == "mount.share_link.gone"


def test_api_mount_share_links_browse_known_token_missing_target_is_410(settings):
    """Known token with missing target path returns 410."""
    settings.MOUNTS_REGISTRY = [_make_static_mount(mount_id="alpha-mount")]

    token = secrets.token_urlsafe(16)
    models.MountShareLink.objects.create(
        token=token,
        mount_id="alpha-mount",
        normalized_path="/missing",
        created_by=None,
    )

    response = APIClient().get(f"/api/v1.0/mount-share-links/{token}/browse/")
    assert response.status_code == 410
    assert response.json()["errors"][0]["code"] == "mount.share_link.gone"


@override_settings(DRIVE_PUBLIC_URL="https://drive.example.com")
def test_api_mount_share_links_browse_success_returns_relative_paths_only(settings):
    """Successful browse returns relative normalized paths (no mount_id/path leaks)."""
    settings.MOUNTS_REGISTRY = [_make_static_mount(mount_id="alpha-mount")]

    token = secrets.token_urlsafe(16)
    models.MountShareLink.objects.create(
        token=token,
        mount_id="alpha-mount",
        normalized_path="/a",
        created_by=None,
    )

    response = APIClient().get(f"/api/v1.0/mount-share-links/{token}/browse/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized_path"] == "/"
    assert "mount_id" not in payload
    assert payload["entry"]["normalized_path"] == "/"
    assert payload["entry"]["entry_type"] == "folder"
    assert payload["children"]["count"] == 1
    assert payload["children"]["results"][0]["normalized_path"] == "/b.txt"

