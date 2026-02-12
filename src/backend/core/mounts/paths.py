"""Mount path normalization helpers (contract-level, deterministic)."""

from __future__ import annotations

import posixpath


class MountPathNormalizationError(ValueError):
    """Raised when a mount path cannot be normalized safely."""


def normalize_mount_path(raw: str | None) -> str:
    """
    Normalize a mount path into a deterministic absolute POSIX-like path.

    Rules:
    - Root is always `/`.
    - A missing/blank path normalizes to `/`.
    - Paths are forced to be absolute (leading `/`).
    - `.` segments are removed.
    - `..` segments are rejected (prevents traversal outside mount root).
    - Duplicate slashes are collapsed.
    """

    if raw is None:
        return "/"

    path = str(raw).strip()
    if not path:
        return "/"

    if "\x00" in path:
        raise MountPathNormalizationError("NUL bytes are not allowed in paths.")

    path = path.replace("\\", "/")
    if not path.startswith("/"):
        path = "/" + path

    while "//" in path:
        path = path.replace("//", "/")

    segments = [seg for seg in path.split("/") if seg not in ("", ".")]
    if any(seg == ".." for seg in segments):
        raise MountPathNormalizationError("Parent path traversal is not allowed.")

    normalized = "/" + "/".join(segments)
    normalized = posixpath.normpath(normalized)
    return "/" if normalized == "." else normalized


def parent_mount_path(path: str) -> str:
    """Return the normalized parent path for a normalized path."""

    normalized = normalize_mount_path(path)
    if normalized == "/":
        return "/"
    return posixpath.dirname(normalized) or "/"
