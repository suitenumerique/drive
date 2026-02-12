"""Mounts registry parsing + deterministic validation (no-leak)."""

from __future__ import annotations

import dataclasses
import re
from typing import Any

from core.mounts.paths import MountPathNormalizationError, normalize_mount_path


@dataclasses.dataclass(frozen=True, slots=True)
class MountRegistryValidationError(Exception):
    """Deterministic validation error with operator guidance."""

    failure_class: str
    next_action_hint: str


_MOUNT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}[a-z0-9]$")
_SECRET_ENV_NAME_RE = re.compile(r"^[A-Z0-9_]{1,128}$")


def _normalize_optional_secret_ref(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_type")
    candidate = value.strip()
    if not candidate:
        return None
    if not _SECRET_ENV_NAME_RE.fullmatch(candidate):
        raise ValueError("invalid_value")
    return candidate


def _normalize_optional_secret_path(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_type")
    candidate = value.strip()
    return candidate or None


def _normalize_required_str(params: dict[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}.missing")
    return value.strip()


def _normalize_optional_timeout_seconds(value: Any) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError("invalid_type")
    if value < 1:
        raise ValueError("invalid_value")
    return value


def _normalize_smb_params(  # noqa: PLR0912
    params: dict[str, Any],
) -> dict[str, Any]:  # pylint: disable=too-many-branches
    """Normalize SMB mount params with defaults (deterministic, no-leak)."""

    normalized = dict(params)
    normalized["server"] = _normalize_required_str(normalized, "server")
    normalized["share"] = _normalize_required_str(normalized, "share")
    normalized["username"] = _normalize_required_str(normalized, "username")

    port = normalized.get("port", 445)
    if port is None:
        port = 445
    if not isinstance(port, int):
        raise ValueError("port.invalid_type")
    if port < 1 or port > 65535:
        raise ValueError("port.invalid_value")
    normalized["port"] = port

    domain = normalized.get("domain")
    if domain is None:
        domain = normalized.get("workgroup")
    if domain is not None:
        if not isinstance(domain, str):
            raise ValueError("domain.invalid_type")
        domain = domain.strip()
        if not domain:
            domain = None
    if domain is not None:
        normalized["domain"] = domain

    base_path = normalized.get("base_path")
    if base_path is not None:
        if not isinstance(base_path, str):
            raise ValueError("base_path.invalid_type")
        try:
            normalized["base_path"] = normalize_mount_path(base_path)
        except MountPathNormalizationError as exc:
            raise ValueError("base_path.invalid_value") from exc

    for timeout_key in (
        "connect_timeout_seconds",
        "operation_timeout_seconds",
        "timeout_seconds",
    ):
        if timeout_key not in normalized:
            continue
        normalized[timeout_key] = _normalize_optional_timeout_seconds(
            normalized.get(timeout_key)
        )

    return normalized


def _is_json_primitive(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_primitive(v) for v in value)
    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_json_primitive(v) for k, v in value.items()
        )
    return False


def validate_mounts_registry(  # noqa: PLR0912, PLR0915
    raw: Any,
) -> list[dict[str, Any]]:  # pylint: disable=too-many-branches,too-many-statements
    """
    Validate mounts registry definitions.

    Input schema (list of dict):
    - mount_id: required, stable unique id (lowercase, [a-z0-9._-], 3..64 chars)
    - display_name: required, non-empty string
    - provider: required, non-empty string
    - enabled: optional bool (default true)
    - params: optional dict (default {}), JSON-serializable, non-secret
    - password_secret_ref: optional env var name (refs-only)
    - password_secret_path: optional file path (refs-only)
    """
    if raw is None:
        return []

    if not isinstance(raw, list):
        raise MountRegistryValidationError(
            failure_class="mount.config.registry.invalid_type",
            next_action_hint="Set mounts registry as a JSON list of mount objects.",
        )

    mounts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise MountRegistryValidationError(
                failure_class="mount.config.entry.invalid_type",
                next_action_hint=(
                    "Ensure each mount entry is a JSON object "
                    f"(failed at mounts[{idx}])."
                ),
            )

        mount_id = entry.get("mount_id")
        if not isinstance(mount_id, str) or not mount_id.strip():
            raise MountRegistryValidationError(
                failure_class="mount.config.mount_id.missing",
                next_action_hint="Set mounts[*].mount_id to a non-empty string.",
            )
        mount_id = mount_id.strip()

        if mount_id.lower() != mount_id or not _MOUNT_ID_RE.match(mount_id):
            raise MountRegistryValidationError(
                failure_class="mount.config.mount_id.invalid",
                next_action_hint=(
                    "Use a lowercase mount_id (3..64 chars) with "
                    "only [a-z0-9._-], starting and ending with [a-z0-9]."
                ),
            )

        if mount_id in seen_ids:
            raise MountRegistryValidationError(
                failure_class="mount.config.mount_id.duplicate",
                next_action_hint="Ensure every mounts[*].mount_id is unique.",
            )
        seen_ids.add(mount_id)

        display_name = entry.get("display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            raise MountRegistryValidationError(
                failure_class="mount.config.display_name.missing",
                next_action_hint="Set mounts[*].display_name to a non-empty string.",
            )

        provider = entry.get("provider")
        if not isinstance(provider, str) or not provider.strip():
            raise MountRegistryValidationError(
                failure_class="mount.config.provider.missing",
                next_action_hint="Set mounts[*].provider to a non-empty string.",
            )
        provider = provider.strip().lower()

        enabled = entry.get("enabled", True)
        if not isinstance(enabled, bool):
            raise MountRegistryValidationError(
                failure_class="mount.config.enabled.invalid_type",
                next_action_hint="Set mounts[*].enabled to a boolean (true/false).",
            )

        params = entry.get("params", {}) or {}
        if not isinstance(params, dict):
            raise MountRegistryValidationError(
                failure_class="mount.config.params.invalid_type",
                next_action_hint="Set mounts[*].params to a JSON object.",
            )
        if not _is_json_primitive(params):
            raise MountRegistryValidationError(
                failure_class="mount.config.params.invalid_value",
                next_action_hint=(
                    "Ensure mounts[*].params contains only JSON-serializable "
                    "values (strings/numbers/bools/lists/objects/null)."
                ),
            )

        if isinstance(entry.get("password"), str) and entry.get("password").strip():
            raise MountRegistryValidationError(
                failure_class="mount.config.secrets.direct_value_forbidden",
                next_action_hint=(
                    "Do not set mount passwords directly. Use refs-only fields "
                    "like `password_secret_ref` and/or `password_secret_path`."
                ),
            )
        if isinstance(params.get("password"), str) and params.get("password").strip():
            raise MountRegistryValidationError(
                failure_class="mount.config.secrets.direct_value_forbidden",
                next_action_hint=(
                    "Do not set mount passwords directly. Use refs-only fields "
                    "like `password_secret_ref` and/or `password_secret_path`."
                ),
            )

        try:
            password_secret_ref = _normalize_optional_secret_ref(
                entry.get("password_secret_ref")
            )
        except ValueError as exc:
            reason = str(exc)
            mapping = {
                "invalid_type": (
                    "mount.config.secrets.secret_ref.invalid_type",
                    "Set mounts[*].password_secret_ref to an env var name string.",
                ),
                "invalid_value": (
                    "mount.config.secrets.secret_ref.invalid",
                    "Use an env var name like MOUNT_PASSWORD (A-Z0-9_).",
                ),
            }
            fc, hint = mapping.get(
                reason,
                (
                    "mount.config.secrets.secret_ref.invalid",
                    "Use an env var name like MOUNT_PASSWORD (A-Z0-9_).",
                ),
            )
            raise MountRegistryValidationError(
                failure_class=fc,
                next_action_hint=hint,
            ) from None

        try:
            password_secret_path = _normalize_optional_secret_path(
                entry.get("password_secret_path")
            )
        except ValueError:
            raise MountRegistryValidationError(
                failure_class="mount.config.secrets.secret_path.invalid_type",
                next_action_hint="Set mounts[*].password_secret_path to a file path string.",
            ) from None

        if provider == "smb":
            try:
                params = _normalize_smb_params(params)
            except ValueError as exc:
                reason = str(exc)
                mapping = {
                    "server.missing": (
                        "mount.config.smb.server.missing",
                        "Set mounts[*].params.server to a non-empty string (host/IP).",
                    ),
                    "share.missing": (
                        "mount.config.smb.share.missing",
                        "Set mounts[*].params.share to a non-empty string.",
                    ),
                    "username.missing": (
                        "mount.config.smb.username.missing",
                        "Set mounts[*].params.username to a non-empty string.",
                    ),
                    "port.invalid_type": (
                        "mount.config.smb.port.invalid_type",
                        "Set mounts[*].params.port to an integer (default 445).",
                    ),
                    "port.invalid_value": (
                        "mount.config.smb.port.invalid_value",
                        "Set mounts[*].params.port to an integer between 1 and 65535.",
                    ),
                    "domain.invalid_type": (
                        "mount.config.smb.domain.invalid_type",
                        "Set mounts[*].params.domain/workgroup to a string, or omit it.",
                    ),
                    "base_path.invalid_type": (
                        "mount.config.smb.base_path.invalid_type",
                        "Set mounts[*].params.base_path to a mount path string like '/subdir'.",
                    ),
                    "base_path.invalid_value": (
                        "mount.config.smb.base_path.invalid_value",
                        "Set mounts[*].params.base_path to a valid mount path without '..'.",
                    ),
                    "invalid_type": (
                        "mount.config.smb.timeout.invalid_type",
                        "Set SMB timeout fields to integers (seconds), or omit them.",
                    ),
                    "invalid_value": (
                        "mount.config.smb.timeout.invalid_value",
                        "Set SMB timeout fields to integers >= 1 (seconds).",
                    ),
                }
                fc, hint = mapping.get(
                    reason,
                    (
                        "mount.config.smb.invalid",
                        "Fix SMB mount params and retry validation.",
                    ),
                )
                raise MountRegistryValidationError(
                    failure_class=fc,
                    next_action_hint=hint,
                ) from None

        mounts.append(
            {
                "mount_id": mount_id,
                "display_name": display_name.strip(),
                "provider": provider,
                "enabled": enabled,
                "params": params,
                **(
                    {"password_secret_ref": password_secret_ref}
                    if password_secret_ref
                    else {}
                ),
                **(
                    {"password_secret_path": password_secret_path}
                    if password_secret_path
                    else {}
                ),
            }
        )

    mounts.sort(key=lambda m: m["mount_id"])
    return mounts
