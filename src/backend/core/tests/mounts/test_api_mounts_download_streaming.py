"""Tests for mount download streaming + Range semantics (SMB provider)."""

from __future__ import annotations

import contextlib
import io

import pytest
from rest_framework.test import APIClient

from core import factories
from core.mounts.providers.base import MountEntry

pytestmark = pytest.mark.django_db


def _make_smb_mount(*, mount_id: str) -> dict:
    return {
        "mount_id": mount_id,
        "display_name": mount_id,
        "provider": "smb",
        "enabled": True,
        "params": {},
    }


def test_api_mount_download_streams_full_response(monkeypatch, settings):
    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]

    content = b"0123456789"

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:  # noqa: ARG001
        return MountEntry(
            entry_type="file",
            normalized_path=normalized_path,
            name="file.bin",
            size=len(content),
            modified_at=None,
        )

    @contextlib.contextmanager
    def _fake_open_read(*, mount: dict, normalized_path: str):  # noqa: ARG001
        yield io.BytesIO(content)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_read", _fake_open_read)
    monkeypatch.setattr(
        "core.mounts.providers.smb.supports_range_reads", lambda **_: True
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get("/api/v1.0/mounts/alpha-mount/download/?path=/file.bin")
    assert resp.status_code == 200
    assert resp["Content-Length"] == str(len(content))
    assert b"".join(resp.streaming_content) == content


def test_api_mount_download_supports_single_range(monkeypatch, settings):
    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]

    content = b"0123456789"

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:  # noqa: ARG001
        return MountEntry(
            entry_type="file",
            normalized_path=normalized_path,
            name="file.bin",
            size=len(content),
            modified_at=None,
        )

    @contextlib.contextmanager
    def _fake_open_read(*, mount: dict, normalized_path: str):  # noqa: ARG001
        yield io.BytesIO(content)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_read", _fake_open_read)
    monkeypatch.setattr(
        "core.mounts.providers.smb.supports_range_reads", lambda **_: True
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get(
        "/api/v1.0/mounts/alpha-mount/download/?path=/file.bin",
        HTTP_RANGE="bytes=0-3",
    )
    assert resp.status_code == 206
    assert resp["Content-Length"] == "4"
    assert resp["Content-Range"] == f"bytes 0-3/{len(content)}"
    assert b"".join(resp.streaming_content) == b"0123"


def test_api_mount_download_rejects_unsatisfiable_range(monkeypatch, settings):
    settings.MOUNTS_REGISTRY = [_make_smb_mount(mount_id="alpha-mount")]

    content = b"0123456789"

    def _fake_stat(*, mount: dict, normalized_path: str) -> MountEntry:  # noqa: ARG001
        return MountEntry(
            entry_type="file",
            normalized_path=normalized_path,
            name="file.bin",
            size=len(content),
            modified_at=None,
        )

    @contextlib.contextmanager
    def _fake_open_read(*, mount: dict, normalized_path: str):  # noqa: ARG001
        yield io.BytesIO(content)

    monkeypatch.setattr("core.mounts.providers.smb.stat", _fake_stat)
    monkeypatch.setattr("core.mounts.providers.smb.open_read", _fake_open_read)
    monkeypatch.setattr(
        "core.mounts.providers.smb.supports_range_reads", lambda **_: True
    )

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    resp = client.get(
        "/api/v1.0/mounts/alpha-mount/download/?path=/file.bin",
        HTTP_RANGE="bytes=999-",
    )
    assert resp.status_code == 416
    assert resp["Content-Range"] == f"bytes */{len(content)}"
