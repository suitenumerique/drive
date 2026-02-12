"""Mounts registry parsing + deterministic validation (no-leak)."""

from __future__ import annotations

import dataclasses
import re
from typing import Any


@dataclasses.dataclass(frozen=True, slots=True)
class MountRegistryValidationError(Exception):
    """Deterministic validation error with operator guidance."""

    failure_class: str
    next_action_hint: str


_MOUNT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,62}[a-z0-9]$")


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


def validate_mounts_registry(raw: Any) -> list[dict[str, Any]]:
    """
    Validate mounts registry definitions.

    Input schema (list of dict):
    - mount_id: required, stable unique id (lowercase, [a-z0-9._-], 3..64 chars)
    - display_name: required, non-empty string
    - provider: required, non-empty string
    - enabled: optional bool (default true)
    - params: optional dict (default {}), JSON-serializable, non-secret
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

        mounts.append(
            {
                "mount_id": mount_id,
                "display_name": display_name.strip(),
                "provider": provider,
                "enabled": enabled,
                "params": params,
            }
        )

    mounts.sort(key=lambda m: m["mount_id"])
    return mounts
