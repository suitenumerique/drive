"""SMB MountProvider (v1: stat + list_children)."""

from __future__ import annotations

import dataclasses
import errno
import posixpath
import stat as statlib
import threading
from datetime import datetime, timezone
from typing import Any

import smbclient
from smbprotocol.exceptions import (
    AccessDenied,
    BadNetworkName,
    LogonFailure,
    NoSuchFile,
    ObjectNameNotFound,
    ObjectPathNotFound,
    PasswordExpired,
    SMBAuthenticationError,
    SMBConnectionClosed,
    SMBOSError,
    WrongPassword,
)

from core.mounts.paths import MountPathNormalizationError, normalize_mount_path
from core.mounts.providers.base import MountEntry, MountProviderError
from core.services.secret_resolver import get_mount_secret_resolver
from core.utils.rotating_resource import RotatingResource, RotatingResourceError
from core.utils.secret_resolver import SecretResolutionError


@dataclasses.dataclass(frozen=True, slots=True)
class _SmbConfig:
    server: str
    share: str
    username: str
    port: int
    domain: str | None
    base_path: str
    connect_timeout_seconds: int

    @property
    def auth_username(self) -> str:
        """Return the SMB auth username (domain\\username when domain is set)."""

        if not self.domain:
            return self.username
        return f"{self.domain}\\{self.username}"


_SESSION_LOCK = threading.Lock()
_SESSIONS: dict[
    str, RotatingResource[tuple[_SmbConfig, str], tuple[str, str, int, str]]
] = {}


def _config_error(*, failure_class: str, next_action_hint: str) -> MountProviderError:
    return MountProviderError(
        failure_class=failure_class,
        next_action_hint=next_action_hint,
        public_message="Mount provider configuration is invalid.",
        public_code="mount.provider.invalid_config",
    )


def _load_config(  # noqa: PLR0912
    mount: dict[str, Any],
) -> tuple[_SmbConfig, str | None, str | None]:
    # pylint: disable=too-many-branches
    params = mount.get("params") if isinstance(mount.get("params"), dict) else {}

    server = str(params.get("server") or "").strip()
    share = str(params.get("share") or "").strip()
    username = str(params.get("username") or "").strip()
    if not server:
        raise _config_error(
            failure_class="mount.smb.config.server_missing",
            next_action_hint="Set mounts[*].params.server for SMB mounts.",
        )
    if not share:
        raise _config_error(
            failure_class="mount.smb.config.share_missing",
            next_action_hint="Set mounts[*].params.share for SMB mounts.",
        )
    if not username:
        raise _config_error(
            failure_class="mount.smb.config.username_missing",
            next_action_hint="Set mounts[*].params.username for SMB mounts.",
        )

    port_raw = params.get("port", 445)
    port = port_raw if isinstance(port_raw, int) else None
    if port is None or port < 1 or port > 65535:
        raise _config_error(
            failure_class="mount.smb.config.port_invalid",
            next_action_hint="Set mounts[*].params.port to an integer between 1 and 65535.",
        )

    domain_raw = params.get("domain")
    if domain_raw is None:
        domain_raw = params.get("workgroup")
    domain = str(domain_raw).strip() if isinstance(domain_raw, str) else None
    if domain == "":
        domain = None

    base_path_raw = params.get("base_path", "/")
    if not isinstance(base_path_raw, str):
        raise _config_error(
            failure_class="mount.smb.config.base_path_invalid",
            next_action_hint=(
                "Set mounts[*].params.base_path to a mount path string like '/subdir'."
            ),
        )
    try:
        base_path = normalize_mount_path(base_path_raw)
    except MountPathNormalizationError as exc:
        raise _config_error(
            failure_class="mount.smb.config.base_path_invalid",
            next_action_hint="Set mounts[*].params.base_path to a valid mount path without '..'.",
        ) from exc

    connect_timeout_seconds_raw = params.get("connect_timeout_seconds", 60)
    connect_timeout_seconds = (
        connect_timeout_seconds_raw
        if isinstance(connect_timeout_seconds_raw, int)
        else None
    )
    if connect_timeout_seconds is None or connect_timeout_seconds < 1:
        raise _config_error(
            failure_class="mount.smb.config.timeout_invalid",
            next_action_hint="Set mounts[*].params.connect_timeout_seconds to an integer >= 1.",
        )

    if isinstance(mount.get("password"), str) and str(mount.get("password")).strip():
        raise _config_error(
            failure_class="mount.smb.config.password_forbidden",
            next_action_hint=(
                "Do not set mount passwords directly; use password_secret_ref and/or "
                "password_secret_path."
            ),
        )
    if isinstance(params.get("password"), str) and str(params.get("password")).strip():
        raise _config_error(
            failure_class="mount.smb.config.password_forbidden",
            next_action_hint=(
                "Do not set mount passwords directly; use password_secret_ref and/or "
                "password_secret_path."
            ),
        )

    secret_ref = mount.get("password_secret_ref") or params.get("password_secret_ref")
    secret_path = mount.get("password_secret_path") or params.get(
        "password_secret_path"
    )
    secret_ref = str(secret_ref).strip() if isinstance(secret_ref, str) else None
    secret_path = str(secret_path).strip() if isinstance(secret_path, str) else None
    if secret_ref == "":
        secret_ref = None
    if secret_path == "":
        secret_path = None

    config = _SmbConfig(
        server=server,
        share=share,
        username=username,
        port=port,
        domain=domain,
        base_path=base_path,
        connect_timeout_seconds=connect_timeout_seconds,
    )
    return config, secret_path, secret_ref


def _session_pool_key(mount: dict[str, Any], config: _SmbConfig) -> str:
    mount_id = str(mount.get("mount_id") or "").strip()
    if mount_id:
        return mount_id
    return f"{config.server}:{config.share}:{config.auth_username}:{config.port}"


def _ensure_session(
    *,
    mount: dict[str, Any],
    config: _SmbConfig,
    secret_path: str | None,
    secret_ref: str | None,
) -> None:
    key = _session_pool_key(mount, config)

    def _credentials_provider() -> tuple[tuple[_SmbConfig, str], str]:
        resolver = get_mount_secret_resolver()
        resolved = resolver.resolve(secret_path=secret_path, secret_ref=secret_ref)
        version = "|".join(
            [
                config.server,
                config.auth_username,
                str(config.port),
                str(config.connect_timeout_seconds),
                resolved.version_sha256_16,
            ]
        )
        return (config, resolved.value), version

    def _factory(creds: tuple[_SmbConfig, str]) -> tuple[str, str, int, str]:
        cfg, password = creds
        smbclient.register_session(
            cfg.server,
            username=cfg.auth_username,
            password=password,
            port=cfg.port,
            connection_timeout=cfg.connect_timeout_seconds,
        )
        return (cfg.server, cfg.auth_username, cfg.port, "ok")

    with _SESSION_LOCK:
        pool = _SESSIONS.get(key)
        if pool is None:
            pool = RotatingResource(
                credentials_provider=_credentials_provider, factory=_factory
            )
            _SESSIONS[key] = pool

    try:
        _ = pool.get()
    except (RotatingResourceError, SecretResolutionError) as exc:
        if isinstance(exc, SecretResolutionError):
            raise MountProviderError(
                failure_class=exc.failure_class,
                next_action_hint=exc.next_action_hint,
                public_message=exc.public_message,
                public_code=exc.public_code,
            ) from None
        raise MountProviderError(
            failure_class=exc.failure_class,
            next_action_hint=exc.next_action_hint,
            public_message=exc.public_message,
            public_code=exc.public_code,
        ) from None


def _combined_path(*, base_path: str, normalized_path: str) -> str:
    base = normalize_mount_path(base_path)
    target = normalize_mount_path(normalized_path)
    if base == "/":
        return target
    if target == "/":
        return base
    return normalize_mount_path(base.rstrip("/") + target)


def _unc_path(*, config: _SmbConfig, normalized_path: str) -> str:
    combined = _combined_path(
        base_path=config.base_path, normalized_path=normalized_path
    )
    rel = combined.lstrip("/")
    rel_win = rel.replace("/", "\\")
    base = f"\\\\{config.server}\\{config.share}"
    return f"{base}\\{rel_win}" if rel_win else base


def _map_exc(*, exc: Exception, op: str) -> MountProviderError:
    if isinstance(exc, BadNetworkName):
        return MountProviderError(
            failure_class="mount.smb.env.share_not_found",
            next_action_hint="Verify the SMB server/share name and retry the operation.",
            public_message="SMB share not found.",
            public_code="mount.smb.env.share_not_found",
        )

    if isinstance(
        exc,
        (
            SMBAuthenticationError,
            LogonFailure,
            WrongPassword,
            PasswordExpired,
            AccessDenied,
        ),
    ):
        return MountProviderError(
            failure_class="mount.smb.env.auth_failed",
            next_action_hint="Verify SMB credentials (refs-only secrets) and retry the operation.",
            public_message="SMB authentication failed.",
            public_code="mount.smb.env.auth_failed",
        )

    if isinstance(exc, (SMBConnectionClosed, TimeoutError)):
        return MountProviderError(
            failure_class="mount.smb.env.unreachable",
            next_action_hint="Verify the SMB server is reachable from the backend and retry.",
            public_message="SMB mount is unreachable.",
            public_code="mount.smb.env.unreachable",
        )

    if isinstance(exc, OSError) and getattr(exc, "errno", None) in {
        errno.ECONNREFUSED,
        errno.EHOSTUNREACH,
        errno.ENETUNREACH,
        errno.ETIMEDOUT,
    }:
        return MountProviderError(
            failure_class="mount.smb.env.unreachable",
            next_action_hint="Verify the SMB server is reachable from the backend and retry.",
            public_message="SMB mount is unreachable.",
            public_code="mount.smb.env.unreachable",
        )

    if isinstance(
        exc,
        (
            SMBOSError,
            FileNotFoundError,
            NoSuchFile,
            ObjectNameNotFound,
            ObjectPathNotFound,
        ),
    ) or (isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.ENOENT):
        return MountProviderError(
            failure_class="mount.path.not_found",
            next_action_hint="Verify the path exists in the mount and retry.",
            public_message="Mount path not found.",
            public_code="mount.path.not_found",
        )

    failure_class = "mount.smb.stat_failed" if op == "stat" else "mount.smb.list_failed"
    next_action_hint = (
        "Verify SMB mount configuration and connectivity, then retry the stat operation."
        if op == "stat"
        else "Verify SMB mount configuration and connectivity, then retry the list operation."
    )
    return MountProviderError(
        failure_class=failure_class,
        next_action_hint=next_action_hint,
        public_message="SMB operation failed.",
        public_code=failure_class,
    )


def stat(*, mount: dict, normalized_path: str) -> MountEntry:
    """Return metadata for a target path."""
    config, secret_path, secret_ref = _load_config(mount)
    _ensure_session(
        mount=mount,
        config=config,
        secret_path=secret_path,
        secret_ref=secret_ref,
    )

    unc = _unc_path(config=config, normalized_path=normalized_path)
    try:
        st = smbclient.stat(unc)
    except Exception as exc:  # noqa: BLE001
        raise _map_exc(exc=exc, op="stat") from None

    is_dir = statlib.S_ISDIR(getattr(st, "st_mode", 0))
    entry_type = "folder" if is_dir else "file"
    name = (
        "/"
        if normalize_mount_path(normalized_path) == "/"
        else normalized_path.strip("/").split("/")[-1]
    )

    modified_at = None
    if getattr(st, "st_mtime", None) is not None:
        modified_at = datetime.fromtimestamp(float(st.st_mtime), tz=timezone.utc)

    size = None if is_dir else int(getattr(st, "st_size", 0) or 0)

    return MountEntry(
        entry_type=entry_type,
        normalized_path=normalize_mount_path(normalized_path),
        name=str(name),
        size=size,
        modified_at=modified_at,
    )


def list_children(*, mount: dict, normalized_path: str) -> list[MountEntry]:
    """List immediate child entries under a folder path."""
    config, secret_path, secret_ref = _load_config(mount)
    _ensure_session(
        mount=mount,
        config=config,
        secret_path=secret_path,
        secret_ref=secret_ref,
    )

    parent = stat(mount=mount, normalized_path=normalized_path)
    if parent.entry_type != "folder":
        return []

    unc = _unc_path(config=config, normalized_path=normalized_path)
    try:
        raw_children = list(smbclient.scandir(unc))
    except Exception as exc:  # noqa: BLE001
        raise _map_exc(exc=exc, op="list") from None

    children: list[MountEntry] = []
    for child in raw_children:
        name = str(getattr(child, "name", "") or "").strip()
        if not name:
            continue

        try:
            child_path = normalize_mount_path(
                posixpath.join(normalize_mount_path(normalized_path), name)
            )
        except MountPathNormalizationError:
            continue

        try:
            st = child.stat()
        except Exception as exc:  # noqa: BLE001
            raise _map_exc(exc=exc, op="list") from None

        is_dir = statlib.S_ISDIR(getattr(st, "st_mode", 0))
        entry_type = "folder" if is_dir else "file"

        modified_at = None
        if getattr(st, "st_mtime", None) is not None:
            modified_at = datetime.fromtimestamp(float(st.st_mtime), tz=timezone.utc)

        size = None if is_dir else int(getattr(st, "st_size", 0) or 0)
        children.append(
            MountEntry(
                entry_type=entry_type,
                normalized_path=child_path,
                name=name,
                size=size,
                modified_at=modified_at,
            )
        )

    return sorted(
        children,
        key=lambda e: (
            0 if e.entry_type == "folder" else 1,
            str(e.name).casefold(),
            e.normalized_path,
        ),
    )
