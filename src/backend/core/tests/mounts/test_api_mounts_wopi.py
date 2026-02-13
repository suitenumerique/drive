"""Tests for mount-backed WOPI semantics (version, locks, streaming save)."""

from __future__ import annotations

import contextlib
import io
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from core import factories
from core.mounts.providers.base import MountEntry
from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY

pytestmark = pytest.mark.django_db


def _make_smb_mount(*, mount_id: str) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "smb",
        "enabled": True,
        "params": {"capabilities": {"mount.wopi": True}},
    }


def _extract_file_id_from_launch_url(launch_url: str) -> str:
    parsed = urlparse(launch_url)
    wopisrc = parse_qs(parsed.query).get("WOPISrc", [None])[0]
    assert wopisrc, "expected WOPISrc query param in launch_url"
    wopi_path = urlparse(wopisrc).path
    match = re.search(r"/wopi/mount-files/(?P<file_id>[0-9a-f-]+)/?$", wopi_path)
    assert match, f"unexpected WOPISrc path: {wopi_path!r}"
    return match.group("file_id")


def test_api_mount_wopi_init_issues_access_token_and_launch_url(monkeypatch, settings):
    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]
    settings.WOPI_CLIENTS = ["collabora"]

    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {"mimetypes": {}, "extensions": {"txt": "https://wopi.example/edit?"}},
        timeout=60,
    )

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        assert normalized_path == "/hello.txt"
        return MountEntry(
            entry_type="file",
            normalized_path="/hello.txt",
            name="hello.txt",
            size=5,
            modified_at=None,
        )

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get("/api/v1.0/mounts/alpha-mount/wopi/?path=/hello.txt")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["access_token"]
    assert payload["access_token_ttl"]
    assert payload["launch_url"]
    assert "/api/v1.0/wopi/mount-files/" in payload["launch_url"]


def test_wopi_mount_lock_and_put_file_streams_and_updates_version(
    monkeypatch, settings
):
    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]
    settings.WOPI_CLIENTS = ["collabora"]

    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        {"mimetypes": {}, "extensions": {"txt": "https://wopi.example/edit?"}},
        timeout=60,
    )

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    state = {"content": b"old", "modified_at": base, "writes": []}

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        assert normalized_path == "/hello.txt"
        return MountEntry(
            entry_type="file",
            normalized_path="/hello.txt",
            name="hello.txt",
            size=len(state["content"]),
            modified_at=state["modified_at"],
        )

    @contextlib.contextmanager
    def _fake_open_read(*, mount: dict, normalized_path: str):
        _ = mount
        assert normalized_path == "/hello.txt"
        yield io.BytesIO(state["content"])

    @contextlib.contextmanager
    def _fake_open_write(*, mount: dict, normalized_path: str):
        _ = mount
        assert normalized_path == "/hello.txt"

        class _RecordingWriter(io.BytesIO):
            def __init__(self):
                super().__init__()
                self.write_calls = 0

            def write(self, b):  # type: ignore[override]
                self.write_calls += 1
                return super().write(b)

        writer = _RecordingWriter()
        yield writer
        state["content"] = writer.getvalue()
        state["modified_at"] = state["modified_at"] + timedelta(seconds=1)
        state["writes"].append(writer.write_calls)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_read", _fake_open_read)
    monkeypatch.setattr("core.mounts.providers.smb.open_write", _fake_open_write)

    user = factories.UserFactory()
    api = APIClient()
    api.force_login(user)

    init = api.get("/api/v1.0/mounts/alpha-mount/wopi/?path=/hello.txt")
    assert init.status_code == 200
    access_token = init.json()["access_token"]
    file_id = _extract_file_id_from_launch_url(init.json()["launch_url"])

    info1 = api.get(
        f"/api/v1.0/wopi/mount-files/{file_id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert info1.status_code == 200
    version1 = info1.json()["Version"]

    lock = api.post(
        f"/api/v1.0/wopi/mount-files/{file_id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_WOPI_OVERRIDE="LOCK",
        HTTP_X_WOPI_LOCK="lock-1",
    )
    assert lock.status_code == 200

    body = b"a" * (64 * 1024 + 123)
    put = api.post(
        f"/api/v1.0/wopi/mount-files/{file_id}/contents/",
        data=body,
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_WOPI_OVERRIDE="PUT",
        HTTP_X_WOPI_LOCK="lock-1",
    )
    assert put.status_code == 200
    assert state["content"] == body
    assert state["writes"], "expected open_write to be used"
    assert state["writes"][-1] >= 2, "expected chunked streaming writes"
    assert "X-WOPI-ItemVersion" in put.headers

    info2 = api.get(
        f"/api/v1.0/wopi/mount-files/{file_id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert info2.status_code == 200
    assert info2.json()["Version"] != version1

    conflict = api.post(
        f"/api/v1.0/wopi/mount-files/{file_id}/contents/",
        data=b"new",
        content_type="application/octet-stream",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_WOPI_OVERRIDE="PUT",
        HTTP_X_WOPI_LOCK="wrong-lock",
    )
    assert conflict.status_code == 409
    assert conflict.headers.get("X-WOPI-Lock") == "lock-1"

    unlock = api.post(
        f"/api/v1.0/wopi/mount-files/{file_id}/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_WOPI_OVERRIDE="UNLOCK",
        HTTP_X_WOPI_LOCK="lock-1",
    )
    assert unlock.status_code == 200
