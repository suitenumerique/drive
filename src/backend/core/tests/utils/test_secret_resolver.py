import os
from pathlib import Path

import pytest

from core.utils.secret_resolver import SecretResolutionError, SecretResolver


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def tick(self, seconds: float) -> None:
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def test_secret_resolver_precedence_file_over_env(tmp_path, monkeypatch):
    clock = _Clock()
    resolver = SecretResolver(refresh_seconds=60, now_mono=clock)

    monkeypatch.setenv("MOUNT_ALPHA_PASSWORD", "env-secret")
    secret_file = tmp_path / "pw"
    secret_file.write_text("file-secret\n", encoding="utf-8")

    resolved = resolver.resolve(
        secret_path=str(secret_file),
        secret_ref="MOUNT_ALPHA_PASSWORD",
    )

    assert resolved.source == "file"
    assert resolved.value == "file-secret"


def test_secret_resolver_file_detects_change_within_refresh_window(tmp_path):
    clock = _Clock()
    resolver = SecretResolver(refresh_seconds=60, now_mono=clock)

    secret_file = tmp_path / "pw"
    secret_file.write_text("v1\n", encoding="utf-8")

    first = resolver.resolve(secret_path=str(secret_file), secret_ref=None)
    assert first.value == "v1"

    secret_file.write_text("v2\n", encoding="utf-8")
    os.utime(secret_file, None)

    second = resolver.resolve(secret_path=str(secret_file), secret_ref=None)
    assert second.value == "v2"
    assert second.version_sha256_16 != first.version_sha256_16


def test_secret_resolver_env_refresh_is_bounded(monkeypatch):
    clock = _Clock()
    resolver = SecretResolver(refresh_seconds=10, now_mono=clock)

    monkeypatch.setenv("MOUNT_ALPHA_PASSWORD", "v1")
    first = resolver.resolve(secret_path=None, secret_ref="MOUNT_ALPHA_PASSWORD")
    assert first.value == "v1"

    monkeypatch.setenv("MOUNT_ALPHA_PASSWORD", "v2")

    clock.tick(5)
    still_cached = resolver.resolve(secret_path=None, secret_ref="MOUNT_ALPHA_PASSWORD")
    assert still_cached.value == "v1"

    clock.tick(6)
    refreshed = resolver.resolve(secret_path=None, secret_ref="MOUNT_ALPHA_PASSWORD")
    assert refreshed.value == "v2"


def test_secret_resolver_env_missing_is_no_leak(monkeypatch):
    clock = _Clock()
    resolver = SecretResolver(refresh_seconds=60, now_mono=clock)

    monkeypatch.delenv("MOUNT_ALPHA_PASSWORD", raising=False)
    with pytest.raises(SecretResolutionError) as excinfo:
        resolver.resolve(secret_path=None, secret_ref="MOUNT_ALPHA_PASSWORD")

    err = excinfo.value
    assert err.failure_class == "config.secret.env_ref_missing"
    assert err.safe_evidence.get("env_var") == "MOUNT_ALPHA_PASSWORD"


def test_secret_resolver_file_missing_is_no_leak(tmp_path):
    clock = _Clock()
    resolver = SecretResolver(refresh_seconds=60, now_mono=clock)

    missing = Path(tmp_path / "missing").as_posix()
    with pytest.raises(SecretResolutionError) as excinfo:
        resolver.resolve(secret_path=missing, secret_ref=None)

    err = excinfo.value
    assert err.failure_class == "config.secret.file_missing"
    assert "path_sha256_16" in err.safe_evidence
    assert err.safe_evidence["path_sha256_16"] != ""

