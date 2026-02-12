"""Tests for WOPI health snapshot."""

import pytest

from wopi.services.health import get_wopi_health
from wopi.services.s3_prerequisites import S3BucketVersioningCheck

pytestmark = pytest.mark.django_db


def test_wopi_health_unhealthy_when_s3_bucket_versioning_disabled(
    monkeypatch, settings
):
    """WOPI health is deterministically unhealthy when bucket versioning is disabled."""
    settings.WOPI_CLIENTS = ["vendorA"]
    settings.WOPI_SRC_BASE_URL = "https://drive.example.com"

    monkeypatch.setattr(
        "wopi.services.health.check_wopi_s3_bucket_versioning",
        lambda: S3BucketVersioningCheck(
            ok=False,
            status="Disabled",
            failure_class="wopi.prereq.s3.bucket_versioning.disabled",
            next_action_hint="Enable bucket versioning.",
            evidence={"s3_backend_available": True},
        ),
    )

    health = get_wopi_health()
    assert health.enabled is True
    assert health.healthy is False
    assert health.state == "enabled_unhealthy"
    assert health.failure_class == "wopi.prereq.s3.bucket_versioning.disabled"
    assert isinstance(health.next_action_hint, str)
    assert health.evidence is not None
    assert health.evidence["s3_bucket_versioning_status"] == "Disabled"
