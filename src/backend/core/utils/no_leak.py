"""No-leak helpers shared across the Drive backend.

These helpers provide safe correlation primitives (hashes) to avoid logging or
surfacing sensitive values such as object keys, filenames, or paths.
"""

from __future__ import annotations

import hashlib


def sha256_16(value: str) -> str:
    """Return a stable, truncated SHA-256 digest (hex) for safe correlation."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def safe_str_hash(value: str | None) -> str | None:
    """Hash a potentially sensitive string; returns None if missing."""
    if value is None:
        return None
    return sha256_16(value)
