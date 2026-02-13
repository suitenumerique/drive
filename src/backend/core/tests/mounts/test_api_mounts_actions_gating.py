"""Tests for mount action capability gating (no dead actions)."""

from django.core.cache import cache

import pytest
from rest_framework.test import APIClient

from core import factories
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY

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
    "case",
    [
        {
            "cap_key": "mount.preview",
            "endpoint": "preview",
            "disabled_code": "mount.preview.disabled",
            "unavailable_code": "mount.preview.unavailable",
            "method": "get",
        },
        {
            "cap_key": "mount.wopi",
            "endpoint": "wopi",
            "disabled_code": "mount.wopi.disabled",
            "unavailable_code": "mount.wopi.unavailable",
            "method": "get",
        },
        {
            "cap_key": "mount.upload",
            "endpoint": "upload",
            "disabled_code": "mount.upload.disabled",
            "unavailable_code": "mount.upload.unavailable",
            "method": "post",
        },
    ],
)
def test_api_mount_action_is_capability_gated(
    settings,
    case: dict[str, str],
):
    """When capability is false -> 403; when true -> deterministic unavailable."""

    cap_key = case["cap_key"]
    endpoint = case["endpoint"]
    disabled_code = case["disabled_code"]
    unavailable_code = case["unavailable_code"]
    method = case["method"]

    base_caps = {
        "mount.upload": False,
        "mount.preview": False,
        "mount.wopi": False,
        "mount.share_link": False,
    }

    settings.MOUNTS_REGISTRY = [
        _make_mount(mount_id="alpha-mount", capabilities=base_caps)
    ]
    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    if endpoint == "wopi":
        settings.WOPI_CLIENTS = ["collabora"]
        cache.set(
            WOPI_CONFIGURATION_CACHE_KEY,
            {"mimetypes": {}, "extensions": {"txt": "https://wopi.example/edit?"}},
            timeout=60,
        )

    url = f"/api/v1.0/mounts/alpha-mount/{endpoint}/?path=/"
    resp = getattr(client, method)(url)
    assert resp.status_code == 403
    assert resp.json()["errors"][0]["code"] == disabled_code

    caps_enabled = {**base_caps, cap_key: True}
    settings.MOUNTS_REGISTRY = [
        _make_mount(mount_id="alpha-mount", capabilities=caps_enabled)
    ]
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
