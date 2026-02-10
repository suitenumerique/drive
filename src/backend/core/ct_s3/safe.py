"""No-leak helpers for CT-S3 (hashing, evidence shaping)."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping


def sha256_16(value: str) -> str:
    """Return a stable, truncated SHA-256 digest (hex) for safe correlation."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def safe_str_hash(value: str | None) -> str | None:
    """Hash a potentially sensitive string; returns None if missing."""
    if value is None:
        return None
    return sha256_16(value)


def pick_headers(headers: Mapping[str, str], allowed: set[str]) -> dict[str, str]:
    """
    Pick allow-listed headers only.

    Note: callers must ensure `allowed` does not include sensitive headers.
    """
    picked: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in allowed:
            picked[key.lower()] = value
    return picked
