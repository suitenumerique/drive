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
            "params": {"host": "smb.internal"},
        },
        {
            "mount_id": "beta-mount",
            "display_name": "Beta",
            "provider": "smb",
            "enabled": False,
            "params": {"host": "smb.internal"},
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
            "enabled": True,
            "params": {"host": "smb.internal"},
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
