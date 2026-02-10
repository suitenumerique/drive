"""CT-S3 evidence allow-listing tests (no-leak by construction)."""

# pylint: disable=missing-function-docstring

import pytest

from core.ct_s3.evidence import EvidenceValidationError, build_evidence
from core.ct_s3.types import CheckResult


def test_build_evidence_allows_known_fields_and_sorts_keys():
    evidence = build_evidence(
        {
            "status_code": 200,
            "profile_id": "seaweedfs-s3",
            "bucket_hash": "0123456789abcdef",
        }
    )
    assert list(evidence.keys()) == ["bucket_hash", "profile_id", "status_code"]


def test_build_evidence_rejects_unknown_key_no_leak():
    secret = "secret_value_that_must_not_leak"
    with pytest.raises(EvidenceValidationError) as excinfo:
        build_evidence({"not_allowed": secret})

    message = str(excinfo.value)
    assert "not_allowed" not in message
    assert "secret" not in message


def test_build_evidence_rejects_invalid_hash_value_no_leak():
    secret = "not_a_16_hex_hash"
    with pytest.raises(EvidenceValidationError) as excinfo:
        build_evidence({"bucket_hash": secret})

    message = str(excinfo.value)
    assert "not_a_16_hex_hash" not in message


def test_checkresult_enforces_allowlist():
    with pytest.raises(EvidenceValidationError):
        CheckResult(
            check_id="CT-S3-999",
            audience="INTERNAL_PROXY",
            ok=False,
            title="bad evidence",
            evidence={"raw_url": "http://example.invalid"},
        )
