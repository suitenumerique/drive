"""Tests for mounts browse API (deterministic ordering/pagination)."""

import pytest
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


def _make_static_mount(*, mount_id: str, entries: list[dict]) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "static",
        "enabled": True,
        "params": {
            "capabilities": {
                "mount.upload": True,
                "mount.preview": False,
                "mount.wopi": False,
                "mount.share_link": False,
            },
            "static_entries": entries,
        },
    }


def test_api_mounts_browse_root_children_ordering_is_deterministic(settings):
    """Children are sorted folder-first, then casefolded name, then path tie-breaker."""
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(
            mount_id="alpha-mount",
            entries=[
                {"path": "/", "entry_type": "folder", "name": "/"},
                {"path": "/a", "entry_type": "folder", "name": "a"},
                {"path": "/A", "entry_type": "folder", "name": "A"},
                {"path": "/b.txt", "entry_type": "file", "name": "b.txt"},
                {"path": "/B.txt", "entry_type": "file", "name": "B.txt"},
            ],
        )
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1.0/mounts/alpha-mount/browse/?path=/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mount_id"] == "alpha-mount"
    assert payload["normalized_path"] == "/"
    assert payload["entry"]["normalized_path"] == "/"
    assert payload["children"]["count"] == 4
    assert [e["normalized_path"] for e in payload["children"]["results"]] == [
        "/A",
        "/a",
        "/B.txt",
        "/b.txt",
    ]
    assert payload["children"]["results"][0]["abilities"]["children_list"] is True
    assert payload["children"]["results"][-1]["abilities"]["children_list"] is False


def test_api_mounts_browse_pagination_limit_offset(settings):
    """Children list supports limit/offset pagination."""
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(
            mount_id="alpha-mount",
            entries=[
                {"path": "/", "entry_type": "folder"},
                {"path": "/a", "entry_type": "folder"},
                {"path": "/b", "entry_type": "folder"},
                {"path": "/c.txt", "entry_type": "file"},
                {"path": "/d.txt", "entry_type": "file"},
            ],
        )
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get(
        "/api/v1.0/mounts/alpha-mount/browse/?path=/&limit=2&offset=1"
    )
    assert response.status_code == 200
    results = response.json()["children"]["results"]
    assert len(results) == 2
    assert [e["normalized_path"] for e in results] == ["/b", "/c.txt"]


def test_api_mounts_browse_rejects_parent_traversal(settings):
    """`..` is rejected deterministically (no-leak)."""
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(
            mount_id="alpha-mount",
            entries=[
                {"path": "/", "entry_type": "folder"},
            ],
        )
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1.0/mounts/alpha-mount/browse/?path=/../secret")
    assert response.status_code == 400
    assert response.json()["errors"][0]["code"] == "mount.path.invalid"


def test_api_mounts_browse_missing_path_is_404(settings):
    settings.MOUNTS_REGISTRY = [
        _make_static_mount(
            mount_id="alpha-mount",
            entries=[
                {"path": "/", "entry_type": "folder"},
            ],
        )
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1.0/mounts/alpha-mount/browse/?path=/missing")
    assert response.status_code == 404
    assert response.json()["errors"][0]["code"] == "mount.path.not_found"
