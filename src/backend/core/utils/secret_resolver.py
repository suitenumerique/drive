"""Centralized secret resolver (refs-only, deterministic, bounded refresh, no-leak)."""

from __future__ import annotations

import dataclasses
import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Callable, Literal, TypedDict

SecretSource = Literal["file", "env"]


class SecretResolutionEvidence(TypedDict, total=False):
    """Allow-listed, no-leak evidence for operator-facing diagnostics."""

    source: SecretSource
    path_sha256_16: str
    env_var: str
    refresh_seconds: int


@dataclasses.dataclass(frozen=True, slots=True)
class SecretResolutionError(Exception):
    """
    Deterministic, operator-facing secret resolution error (no-leak).

    Client-facing surfaces should not return `safe_evidence` verbatim unless the
    surface is explicitly operator-scoped.
    """

    failure_class: str
    next_action_hint: str
    safe_evidence: SecretResolutionEvidence

    public_message: str = "Secret resolution failed."
    public_code: str = "secret.resolution_failed"


@dataclasses.dataclass(frozen=True, slots=True)
class ResolvedSecret:
    """Resolved secret value with a stable, no-leak version identifier."""

    value: str
    version_sha256_16: str
    source: SecretSource


@dataclasses.dataclass(slots=True)
class _CachedSecret:
    resolved: ResolvedSecret
    resolved_at_mono: float
    file_mtime_ns: int | None = None
    file_size: int | None = None


def _sha256_16(data: bytes) -> str:
    """Compute a short, stable SHA256 prefix for safe evidence/versioning."""

    return hashlib.sha256(data).hexdigest()[:16]


def _path_sha256_16(path: str) -> str:
    """Hash a path string for safe evidence (never include raw paths)."""

    return _sha256_16(path.encode("utf-8", errors="replace"))


class SecretResolver:
    """
    Centralized, provider-agnostic secret resolver.

    Deterministic precedence when both are provided:
    - `*_secret_path` (file) takes precedence over `*_secret_ref` (env).

    Refresh semantics:
    - Secrets are cached for up to `refresh_seconds`.
    - For file-backed secrets, the resolver attempts to refresh early when the
      file `mtime/size` changes (best-effort; still bounded by `refresh_seconds`).

    No-leak:
    - Errors never include secret material or raw file paths.
    - Safe evidence may include env var name and a hash of the path string.
    """

    def __init__(
        self,
        *,
        refresh_seconds: int,
        now_mono: Callable[[], float] | None = None,
    ) -> None:
        if not isinstance(refresh_seconds, int) or refresh_seconds < 1:
            raise ValueError("refresh_seconds must be an int >= 1")

        self._refresh_seconds = refresh_seconds
        self._now_mono = now_mono or time.monotonic
        self._lock = threading.Lock()
        self._cache: dict[tuple[SecretSource, str], _CachedSecret] = {}

    @property
    def refresh_seconds(self) -> int:
        return self._refresh_seconds

    def resolve(
        self,
        *,
        secret_path: str | None,
        secret_ref: str | None,
    ) -> ResolvedSecret:
        """Resolve a secret with deterministic precedence: file path > env ref."""

        path = (secret_path or "").strip() or None
        ref = (secret_ref or "").strip() or None

        if path:
            return self._resolve_file(path)
        if ref:
            return self._resolve_env(ref)

        raise SecretResolutionError(
            failure_class="config.secret.missing",
            next_action_hint="Set *_secret_path or *_secret_ref for this mount/provider.",
            safe_evidence={"refresh_seconds": self._refresh_seconds},
        )

    def _resolve_file(self, path: str) -> ResolvedSecret:
        """Resolve a file-backed secret with bounded refresh semantics."""

        key = ("file", path)
        now = self._now_mono()

        with self._lock:
            cached = self._cache.get(key)

        if cached and (now - cached.resolved_at_mono) < self._refresh_seconds:
            st = _safe_stat(path)
            if st and cached.file_mtime_ns is not None and cached.file_size is not None:
                if (
                    st.st_mtime_ns == cached.file_mtime_ns
                    and st.st_size == cached.file_size
                ):
                    return cached.resolved
            else:
                return cached.resolved

        refreshed = self._read_file(path)
        with self._lock:
            self._cache[key] = refreshed
        return refreshed.resolved

    def _resolve_env(self, env_var: str) -> ResolvedSecret:
        """Resolve an env-backed secret with bounded refresh semantics."""

        key = ("env", env_var)
        now = self._now_mono()

        with self._lock:
            cached = self._cache.get(key)

        if cached and (now - cached.resolved_at_mono) < self._refresh_seconds:
            return cached.resolved

        refreshed = self._read_env(env_var)
        with self._lock:
            self._cache[key] = refreshed
        return refreshed.resolved

    def _read_env(self, env_var: str) -> _CachedSecret:
        """Read and validate an env var secret value (refs-only, no-leak)."""

        value = (os.environ.get(env_var) or "").strip()
        if not value:
            raise SecretResolutionError(
                failure_class="config.secret.env_ref_missing",
                next_action_hint=f"Ensure {env_var!r} is set and non-empty.",
                safe_evidence={
                    "source": "env",
                    "env_var": env_var,
                    "refresh_seconds": self._refresh_seconds,
                },
            )

        raw = value.encode("utf-8", errors="strict")
        resolved = ResolvedSecret(
            value=value, version_sha256_16=_sha256_16(raw), source="env"
        )
        return _CachedSecret(resolved=resolved, resolved_at_mono=self._now_mono())

    def _read_file(self, path: str) -> _CachedSecret:
        """Read and validate a file secret value (refs-only, no-leak)."""

        p = Path(path)
        if not p.exists():
            raise SecretResolutionError(
                failure_class="config.secret.file_missing",
                next_action_hint="Ensure the configured secret file exists.",
                safe_evidence={
                    "source": "file",
                    "path_sha256_16": _path_sha256_16(path),
                    "refresh_seconds": self._refresh_seconds,
                },
            )

        try:
            raw = p.read_bytes()
        except (OSError, PermissionError) as exc:
            raise SecretResolutionError(
                failure_class="config.secret.file_unreadable",
                next_action_hint="Ensure the configured secret file is readable by the process.",
                safe_evidence={
                    "source": "file",
                    "path_sha256_16": _path_sha256_16(path),
                    "refresh_seconds": self._refresh_seconds,
                },
            ) from exc

        if b"\x00" in raw:
            raise SecretResolutionError(
                failure_class="config.secret.malformed",
                next_action_hint="Ensure the configured secret file contains plain text.",
                safe_evidence={
                    "source": "file",
                    "path_sha256_16": _path_sha256_16(path),
                    "refresh_seconds": self._refresh_seconds,
                },
            )

        try:
            value = raw.decode("utf-8").removesuffix("\n")
        except UnicodeDecodeError as exc:
            raise SecretResolutionError(
                failure_class="config.secret.malformed",
                next_action_hint="Ensure the configured secret file is UTF-8 encoded text.",
                safe_evidence={
                    "source": "file",
                    "path_sha256_16": _path_sha256_16(path),
                    "refresh_seconds": self._refresh_seconds,
                },
            ) from exc

        if not value.strip():
            raise SecretResolutionError(
                failure_class="config.secret.malformed",
                next_action_hint="Ensure the configured secret file is non-empty.",
                safe_evidence={
                    "source": "file",
                    "path_sha256_16": _path_sha256_16(path),
                    "refresh_seconds": self._refresh_seconds,
                },
            )

        st = _safe_stat(path)
        resolved = ResolvedSecret(
            value=value,
            version_sha256_16=_sha256_16(raw.rstrip(b"\n")),
            source="file",
        )
        return _CachedSecret(
            resolved=resolved,
            resolved_at_mono=self._now_mono(),
            file_mtime_ns=getattr(st, "st_mtime_ns", None) if st else None,
            file_size=getattr(st, "st_size", None) if st else None,
        )


def _safe_stat(path: str):
    """Best-effort `stat` (never raises)."""

    try:
        return os.stat(path)
    except OSError:
        return None
