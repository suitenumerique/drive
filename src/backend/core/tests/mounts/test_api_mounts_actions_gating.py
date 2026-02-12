"""Tests for mount action capability gating (no dead actions)."""

import pytest
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


def _make_mount(*, mount_id: str, capabilities: dict[str, bool]) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "static",
        "enabled": True,
        "params": {
            "capabilities": capabilities,
            "static_entries": [{"path": "/", "entry_type": "folder"}],
        },
    }


@pytest.mark.parametrize(
    ("cap_key", "endpoint", "disabled_code", "unavailable_code", "method"),
    [
        (
            "mount.preview",
            "preview",
            "mount.preview.disabled",
            "mount.preview.unavailable",
            "get",
        ),
        (
            "mount.wopi",
            "wopi",
            "mount.wopi.disabled",
            "mount.wopi.unavailable",
            "get",
        ),
        (
            "mount.upload",
            "upload",
            "mount.upload.disabled",
            "mount.upload.unavailable",
            "post",
        ),
    ],
)
def test_api_mount_action_is_capability_gated(
    settings,
    cap_key: str,
    endpoint: str,
    disabled_code: str,
    unavailable_code: str,
    method: str,
):
    """When capability is false -> 403; when true -> deterministic unavailable."""

    base_caps = {
        "mount.upload": False,
        "mount.preview": False,
        "mount.wopi": False,
        "mount.share_link": False,
    }

    settings.MOUNTS_REGISTRY = [_make_mount(mount_id="alpha-mount", capabilities=base_caps)]
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    url = f"/api/v1.0/mounts/alpha-mount/{endpoint}/?path=/"
    resp = getattr(client, method)(url)
    assert resp.status_code == 403
    assert resp.json()["errors"][0]["code"] == disabled_code

    caps_enabled = {**base_caps, cap_key: True}
    settings.MOUNTS_REGISTRY = [_make_mount(mount_id="alpha-mount", capabilities=caps_enabled)]
    resp2 = getattr(client, method)(url)
    assert resp2.status_code == 400
    assert resp2.json()["errors"][0]["code"] == unavailable_code
    assert "/?path=/" not in str(resp2.json())


def test_api_mount_download_is_deterministically_unavailable(settings):
    """Download endpoint returns a deterministic, no-leak error."""
    settings.MOUNTS_REGISTRY = [
        _make_mount(
            mount_id="alpha-mount",
            capabilities={
                "mount.upload": False,
                "mount.preview": False,
                "mount.wopi": False,
                "mount.share_link": False,
            },
        )
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get("/api/v1.0/mounts/alpha-mount/download/?path=/")
    assert resp.status_code == 400
    assert resp.json()["errors"][0]["code"] == "mount.download.unavailable"

