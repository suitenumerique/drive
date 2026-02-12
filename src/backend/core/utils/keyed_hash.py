"""Keyed (HMAC) hashing helpers for safe evidence (no-leak)."""

from __future__ import annotations

from django.utils.crypto import salted_hmac


def hmac_sha256_16(*, salt: str, value: str) -> str:
    """Return a stable, keyed SHA-256 digest prefix (hex) for correlation."""

    return salted_hmac(str(salt), str(value)).hexdigest()[:16]
