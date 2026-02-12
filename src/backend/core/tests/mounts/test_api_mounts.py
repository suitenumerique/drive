"""Tests for mounts discovery API."""

import pytest
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


def test_api_mounts_list_excludes_disabled_mounts(settings):
    """Disabled mounts should not be exposed to end-user discovery."""
    settings.MOUNTS_REGISTRY = [
        {
            "mount_id": "alpha-mount",
            "display_name": "Alpha",
            "provider": "smb",
            "enabled": True,
            "params": {
                "server": "smb.internal",
                "share": "finance",
                "username": "svc",
            },
        },
        {
            "mount_id": "beta-mount",
            "display_name": "Beta",
            "provider": "smb",
            "enabled": False,
            "params": {
                "server": "smb.internal",
                "share": "finance",
                "username": "svc",
            },
        },
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1.0/mounts/")
    assert response.status_code == 200
    assert response.json() == [
        {
            "mount_id": "alpha-mount",
            "display_name": "Alpha",
            "provider": "smb",
            "capabilities": {
                "mount.upload": False,
                "mount.preview": False,
                "mount.wopi": False,
                "mount.share_link": False,
            },
        }
    ]


def test_api_mounts_retrieve_disabled_is_not_found(settings):
    """Disabled mounts are treated as not found on end-user surfaces."""
    settings.MOUNTS_REGISTRY = [
        {
            "mount_id": "alpha-mount",
            "display_name": "Alpha",
            "provider": "smb",
            "enabled": False,
            "params": {},
        },
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1.0/mounts/alpha-mount/")
    assert response.status_code == 404
    assert response.json()["errors"][0]["code"] == "mount.not_found"


def test_api_mounts_discovery_is_no_leak(settings):
    """Discovery should not expose params or secret fields."""
    settings.MOUNTS_REGISTRY = [
        {
            "mount_id": "alpha-mount",
            "display_name": "Alpha",
            "provider": "smb",
            "enabled": True,
            "params": {
                "server": "smb.internal",
                "share": "finance",
                "username": "svc",
                "capabilities": {"mount.upload": True},
            },
            "password_secret_ref": "MOUNT_ALPHA_PASSWORD",
        },
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1.0/mounts/")
    assert response.status_code == 200
    payload = response.json()[0]
    assert "params" not in payload
    assert "password_secret_ref" not in payload
    assert payload["capabilities"]["mount.upload"] is True
