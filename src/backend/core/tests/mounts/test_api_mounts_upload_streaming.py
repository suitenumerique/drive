"""Tests for mount upload streaming semantics (SMB provider)."""

from __future__ import annotations

import contextlib
import io

from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from rest_framework.test import APIClient

from core import factories
from core.mounts.providers.base import MountEntry, MountProviderError

pytestmark = pytest.mark.django_db


def _make_smb_mount(*, mount_id: str, upload_enabled: bool = True) -> dict:
    """Return a minimal SMB mount registry entry for API tests."""

    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "smb",
        "enabled": True,
        "params": {"capabilities": {"mount.upload": upload_enabled}},
    }


def test_api_mount_upload_streams_to_temp_and_renames(monkeypatch, settings):
    """Upload streams bytes to a temp target and finalizes via rename."""

    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]

    written = io.BytesIO()
    calls: dict[str, list[tuple]] = {"open_write": [], "rename": [], "remove": []}

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        if normalized_path == "/":
            return MountEntry(
                entry_type="folder",
                normalized_path="/",
                name="/",
                size=None,
                modified_at=None,
            )
        raise MountProviderError(
            failure_class="mount.path.not_found",
            next_action_hint="Verify the path exists in the mount and retry.",
            public_message="Mount path not found.",
            public_code="mount.path.not_found",
        )

    @contextlib.contextmanager
    def _fake_open_write(*, mount: dict, normalized_path: str):
        _ = mount
        calls["open_write"].append((normalized_path,))
        written.seek(0)
        written.truncate(0)
        yield written

    def _fake_rename(
        *, mount: dict, src_normalized_path: str, dst_normalized_path: str
    ):
        _ = mount
        calls["rename"].append((src_normalized_path, dst_normalized_path))

    def _fake_remove(*, mount: dict, normalized_path: str):
        _ = mount
        calls["remove"].append((normalized_path,))

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_write", _fake_open_write)
    monkeypatch.setattr("core.mounts.providers.smb.rename", _fake_rename)
    monkeypatch.setattr("core.mounts.providers.smb.remove", _fake_remove)

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file = SimpleUploadedFile("hello.txt", b"hello", content_type="text/plain")
    resp = client.post(
        "/api/v1.0/mounts/alpha-mount/upload/?path=/",
        data={"file": file},
        format="multipart",
    )

    assert resp.status_code == 201
    assert resp.json()["normalized_path"] == "/hello.txt"
    assert written.getvalue() == b"hello"
    assert calls["open_write"], "expected open_write to be called"
    assert calls["rename"] == [(calls["open_write"][0][0], "/hello.txt")]


def test_api_mount_upload_rejects_existing_target(monkeypatch, settings):
    """Upload fails deterministically when the final target already exists."""

    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        if normalized_path == "/":
            return MountEntry(
                entry_type="folder",
                normalized_path="/",
                name="/",
                size=None,
                modified_at=None,
            )
        if normalized_path == "/hello.txt":
            return MountEntry(
                entry_type="file",
                normalized_path="/hello.txt",
                name="hello.txt",
                size=5,
                modified_at=None,
            )
        raise MountProviderError(
            failure_class="mount.path.not_found",
            next_action_hint="Verify the path exists in the mount and retry.",
            public_message="Mount path not found.",
            public_code="mount.path.not_found",
        )

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr(
        "core.mounts.providers.smb.remove", lambda **_: None
    )  # stale tmp cleanup

    @contextlib.contextmanager
    def _fake_open_write(**_kwargs):
        yield io.BytesIO()

    monkeypatch.setattr("core.mounts.providers.smb.open_write", _fake_open_write)
    monkeypatch.setattr("core.mounts.providers.smb.rename", lambda **_: None)

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file = SimpleUploadedFile("hello.txt", b"hello", content_type="text/plain")
    resp = client.post(
        "/api/v1.0/mounts/alpha-mount/upload/?path=/",
        data={"file": file},
        format="multipart",
    )

    assert resp.status_code == 400
    assert resp.json()["errors"][0]["code"] == "mount.upload.target_exists"


def test_api_mount_upload_rejects_too_large(monkeypatch, settings):
    """Upload enforces max bytes and cleans up temp best-effort."""

    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]
    settings.MOUNTS_UPLOAD_MAX_BYTES = 3

    written = io.BytesIO()
    removed: list[str] = []

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:
        _ = mount
        if normalized_path == "/":
            return MountEntry(
                entry_type="folder",
                normalized_path="/",
                name="/",
                size=None,
                modified_at=None,
            )
        raise MountProviderError(
            failure_class="mount.path.not_found",
            next_action_hint="Verify the path exists in the mount and retry.",
            public_message="Mount path not found.",
            public_code="mount.path.not_found",
        )

    @contextlib.contextmanager
    def _fake_open_write(*, mount: dict, normalized_path: str):
        _ = (mount, normalized_path)
        written.seek(0)
        written.truncate(0)
        yield written

    def _fake_remove(*, mount: dict, normalized_path: str):
        _ = mount
        removed.append(normalized_path)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_write", _fake_open_write)
    monkeypatch.setattr("core.mounts.providers.smb.rename", lambda **_: None)
    monkeypatch.setattr("core.mounts.providers.smb.remove", _fake_remove)

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    file = SimpleUploadedFile("hello.txt", b"hello", content_type="text/plain")
    resp = client.post(
        "/api/v1.0/mounts/alpha-mount/upload/?path=/",
        data={"file": file},
        format="multipart",
    )

    assert resp.status_code == 400
    assert resp.json()["errors"][0]["code"] == "mount.upload.too_large"
    assert removed, "expected temp cleanup remove() calls"
