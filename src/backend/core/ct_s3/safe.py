"""No-leak helpers for CT-S3 (hashing, evidence shaping)."""

from __future__ import annotations

from collections.abc import Mapping

# Re-export safe hashing helpers for CT-S3 callers.
from core.utils.no_leak import safe_str_hash, sha256_16  # pylint: disable=unused-import


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
