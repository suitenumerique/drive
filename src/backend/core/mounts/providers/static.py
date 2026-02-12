"""Static MountProvider (test/demo-only).

This provider reads a pre-declared tree from mount params and is intended only
for deterministic contract tests and demos. It performs no IO.
"""

from __future__ import annotations

from core.mounts.paths import (
    MountPathNormalizationError,
    normalize_mount_path,
    parent_mount_path,
)
from core.mounts.providers.base import MountEntry, MountProviderError


def _parse_entries(mount: dict) -> dict[str, MountEntry]:
    params = mount.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    raw_entries = params.get("static_entries") or []
    if not isinstance(raw_entries, list):
        raise MountProviderError(
            failure_class="mount.provider.static.invalid_entries",
            next_action_hint="Set mounts[*].params.static_entries as a JSON list.",
            public_message="Mount provider configuration is invalid.",
            public_code="mount.provider.invalid_config",
        )

    entries: dict[str, MountEntry] = {}
    for idx, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise MountProviderError(
                failure_class="mount.provider.static.entry.invalid_type",
                next_action_hint=(
                    "Ensure mounts[*].params.static_entries contains only objects "
                    f"(failed at index {idx})."
                ),
                public_message="Mount provider configuration is invalid.",
                public_code="mount.provider.invalid_config",
            )

        try:
            normalized_path = normalize_mount_path(raw.get("path"))
        except MountPathNormalizationError as exc:
            raise MountProviderError(
                failure_class="mount.provider.static.entry.invalid_path",
                next_action_hint=(
                    "Fix mounts[*].params.static_entries[*].path to a valid mount path."
                ),
                public_message="Mount provider configuration is invalid.",
                public_code="mount.provider.invalid_config",
            ) from exc

        entry_type = raw.get("entry_type")
        if entry_type not in ("file", "folder"):
            raise MountProviderError(
                failure_class="mount.provider.static.entry.invalid_type_value",
                next_action_hint=(
                    "Set mounts[*].params.static_entries[*].entry_type to "
                    "'file' or 'folder'."
                ),
                public_message="Mount provider configuration is invalid.",
                public_code="mount.provider.invalid_config",
            )

        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            derived = (
                normalized_path.strip("/").split("/")[-1]
                if normalized_path != "/"
                else "/"
            )
            name = derived

        size = raw.get("size")
        if size is not None and not isinstance(size, int):
            size = None

        entries[normalized_path] = MountEntry(
            entry_type=entry_type,
            normalized_path=normalized_path,
            name=str(name),
            size=size,
            modified_at=None,
        )

    if "/" not in entries:
        entries["/"] = MountEntry(
            entry_type="folder",
            normalized_path="/",
            name="/",
            size=None,
            modified_at=None,
        )

    return entries


def stat(*, mount: dict, normalized_path: str) -> MountEntry:
    """Return metadata for a target path."""
    entries = _parse_entries(mount)
    try:
        return entries[normalized_path]
    except KeyError as exc:
        raise MountProviderError(
            failure_class="mount.path.not_found",
            next_action_hint="Verify the path exists in the mount and retry.",
            public_message="Mount path not found.",
            public_code="mount.path.not_found",
        ) from exc


def list_children(*, mount: dict, normalized_path: str) -> list[MountEntry]:
    """List immediate child entries under a folder path."""
    entries = _parse_entries(mount)
    parent = entries.get(normalized_path)
    if parent is None:
        raise MountProviderError(
            failure_class="mount.path.not_found",
            next_action_hint="Verify the path exists in the mount and retry.",
            public_message="Mount path not found.",
            public_code="mount.path.not_found",
        )
    if parent.entry_type != "folder":
        return []

    children: list[MountEntry] = []
    for p, entry in entries.items():
        if p == normalized_path:
            continue
        if parent_mount_path(p) != normalized_path:
            continue
        children.append(entry)

    return children
