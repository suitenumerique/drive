"""Evidence allow-listing for CT-S3 (no-leak by construction)."""

from __future__ import annotations

import re
from typing import Any


class EvidenceValidationError(ValueError):
    """Raised when CT-S3 evidence violates the allow-list or type constraints."""


_HASH16_RE = re.compile(r"^[0-9a-f]{16}$")


ALLOWED_EVIDENCE_KEYS: set[str] = {
    # Profile context (hashed)
    "profile_id",
    "bucket_hash",
    "internal_endpoint_hash",
    "external_signed_base_hash",
    # Host / key correlation (hashed)
    "signed_host_hash",
    "expected_host_hash",
    "internal_host_hash",
    "object_key_hash",
    # HTTP / S3 evidence (safe)
    "status_code",
    "request_id",
    "attempts",
    "strict_range_206",
    "signed_headers_includes_x_amz_acl",
    "signed_host_matches_internal_endpoint",
}


def build_evidence(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Enforce allow-listed evidence keys and safe value shapes.

    This function must never echo sensitive values in exceptions.
    """
    unknown_keys = sorted(set(raw) - ALLOWED_EVIDENCE_KEYS)
    if unknown_keys:
        raise EvidenceValidationError("CT-S3 evidence contains a non-allowlisted key.")

    out: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None:
            out[key] = None
            continue

        if key.endswith("_hash"):
            if not isinstance(value, str) or _HASH16_RE.fullmatch(value) is None:
                raise EvidenceValidationError(
                    "CT-S3 evidence hash value is not a 16-hex digest."
                )
            out[key] = value
            continue

        if key in {"status_code", "attempts"}:
            if not isinstance(value, int):
                raise EvidenceValidationError("CT-S3 evidence integer field is invalid.")
            out[key] = value
            continue

        if key in {
            "strict_range_206",
            "signed_headers_includes_x_amz_acl",
            "signed_host_matches_internal_endpoint",
        }:
            if not isinstance(value, bool):
                raise EvidenceValidationError("CT-S3 evidence boolean field is invalid.")
            out[key] = value
            continue

        if key in {"profile_id", "request_id"}:
            if not isinstance(value, str):
                raise EvidenceValidationError("CT-S3 evidence string field is invalid.")
            out[key] = value
            continue

        raise EvidenceValidationError("CT-S3 evidence contains an invalid field.")

    return dict(sorted(out.items(), key=lambda kv: kv[0]))
