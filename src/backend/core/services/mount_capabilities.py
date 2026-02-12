"""Mount capability keys and normalization helpers (contract-level)."""

from __future__ import annotations

from typing import Any

MOUNT_CAPABILITY_KEYS: tuple[str, ...] = (
    "mount.upload",
    "mount.preview",
    "mount.wopi",
    "mount.share_link",
)


def normalize_mount_capabilities(raw: Any) -> dict[str, bool]:
    """
    Normalize a raw capabilities object into a contract-level capability map.

    - Keys are enforced to the documented constants.
    - Values must be booleans; anything else is treated as `False`.
    """

    if not isinstance(raw, dict):
        raw = {}

    normalized: dict[str, bool] = {}
    for key in MOUNT_CAPABILITY_KEYS:
        value = raw.get(key, False)
        normalized[key] = value if isinstance(value, bool) else False
    return normalized

