"""Tests for mount preview behavior (SMB provider)."""

from __future__ import annotations

import contextlib
import io

import pytest
from rest_framework.test import APIClient

from core import factories
from core.mounts.providers.base import MountEntry, MountProviderError

pytestmark = pytest.mark.django_db


def _make_smb_mount(*, mount_id: str, preview_enabled: bool) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "smb",
        "enabled": True,
        "params": {"capabilities": {"mount.preview": preview_enabled}},
    }


def test_api_mount_preview_streams_when_enabled(monkeypatch, settings):
    """When mount.preview is enabled and file is previewable -> 200 streaming."""

    settings.MOUNTS_REGISTRY = [
        _make_smb_mount(mount_id="alpha-mount", preview_enabled=True)
    ]
    settings.ITEM_PREVIEWABLE_MIME_TYPES = ["text/"]

    content = b"hello"

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        return MountEntry(
            entry_type="file",
            normalized_path=normalized_path,
            name="hello.txt",
            size=len(content),
            modified_at=None,
        )

    @contextlib.contextmanager
    def _fake_open_read(*, mount: dict, normalized_path: str):
        _ = (mount, normalized_path)
        yield io.BytesIO(content)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_read", _fake_open_read)
    monkeypatch.setattr(
        "core.api.utils.detect_mimetype", lambda *_a, **_k: "text/plain"
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get("/api/v1.0/mounts/alpha-mount/preview/?path=/hello.txt")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/plain")
    assert b"".join(resp.streaming_content) == content


def test_api_mount_preview_returns_not_previewable(monkeypatch, settings):
    """When file is not previewable -> deterministic 400 code."""

    settings.MOUNTS_REGISTRY = [
        _make_smb_mount(mount_id="alpha-mount", preview_enabled=True)
    ]
    settings.ITEM_PREVIEWABLE_MIME_TYPES = ["text/"]

    content = b"\x00\x01\x02"

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        return MountEntry(
            entry_type="file",
            normalized_path=normalized_path,
            name="file.bin",
            size=len(content),
            modified_at=None,
        )

    @contextlib.contextmanager
    def _fake_open_read(*, mount: dict, normalized_path: str):
        _ = (mount, normalized_path)
        yield io.BytesIO(content)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_read", _fake_open_read)
    monkeypatch.setattr(
        "core.api.utils.detect_mimetype", lambda *_a, **_k: "application/octet-stream"
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get("/api/v1.0/mounts/alpha-mount/preview/?path=/file.bin")
    assert resp.status_code == 400
    assert resp.json()["errors"][0]["code"] == "mount.preview.not_previewable"


def test_api_mount_preview_is_capability_gated(monkeypatch, settings):
    """When mount.preview is disabled -> 403."""

    settings.MOUNTS_REGISTRY = [
        _make_smb_mount(mount_id="alpha-mount", preview_enabled=False)
    ]

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get("/api/v1.0/mounts/alpha-mount/preview/?path=/file.bin")
    assert resp.status_code == 403
    assert resp.json()["errors"][0]["code"] == "mount.preview.disabled"
