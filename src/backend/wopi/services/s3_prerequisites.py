"""S3 backend prerequisite checks for WOPI (no-leak, operator-guided)."""

from __future__ import annotations

import dataclasses
from typing import Any

from django.core.cache import cache
from django.core.files.storage import default_storage

WOPI_S3_BUCKET_VERSIONING_CACHE_KEY = "wopi.s3.bucket_versioning"
WOPI_S3_BUCKET_VERSIONING_CACHE_TTL_SECONDS = 300


@dataclasses.dataclass(frozen=True, slots=True)
class S3BucketVersioningCheck:
    """Result for the S3 bucket versioning prerequisite."""

    ok: bool
    status: str
    failure_class: str | None = None
    next_action_hint: str | None = None
    evidence: dict[str, Any] | None = None

    def to_evidence(self) -> dict[str, Any]:
        """Return a JSON-serializable evidence payload (no-leak)."""
        payload = dict(self.evidence or {})
        payload.update(
            {
                "s3_bucket_versioning_status": self.status,
                "s3_bucket_versioning_ok": self.ok,
            }
        )
        return payload


def _get_default_storage_s3_bucket_and_client() -> tuple[str | None, Any | None]:
    """
    Best-effort extraction of the S3 bucket name + boto3-like client.

    This intentionally does not raise: callers should treat missing values as
    "backend unsupported" (not a versioning failure).
    """
    bucket_name = getattr(default_storage, "bucket_name", None)
    connection = getattr(default_storage, "connection", None)
    client = getattr(getattr(connection, "meta", None), "client", None)
    return bucket_name, client


def check_wopi_s3_bucket_versioning(
    *, refresh: bool = False
) -> S3BucketVersioningCheck:
    """
    Validate that the configured S3 bucket has versioning enabled.

    No-leak rules:
    - do not return/log bucket names or endpoint URLs
    - do not echo exception messages
    """
    if not refresh:
        cached = cache.get(WOPI_S3_BUCKET_VERSIONING_CACHE_KEY)
        if isinstance(cached, dict) and "ok" in cached and "status" in cached:
            return S3BucketVersioningCheck(
                ok=bool(cached.get("ok")),
                status=str(cached.get("status")),
                failure_class=cached.get("failure_class"),
                next_action_hint=cached.get("next_action_hint"),
                evidence=cached.get("evidence") or {},
            )

    bucket_name, client = _get_default_storage_s3_bucket_and_client()
    if not bucket_name or not client:
        return S3BucketVersioningCheck(
            ok=False,
            status="unavailable",
            failure_class="wopi.backend.s3.unavailable",
            next_action_hint=(
                "Configure an S3-compatible storage backend (bucket + client) for WOPI."
            ),
            evidence={"s3_backend_available": False},
        )

    try:
        # AWS S3 returns {"Status": "Enabled"|"Suspended"} or {} when disabled.
        resp = client.get_bucket_versioning(Bucket=bucket_name) or {}
        status = (resp.get("Status") or "Disabled").strip() or "Disabled"
    except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        result = S3BucketVersioningCheck(
            ok=False,
            status="Unknown",
            failure_class="wopi.prereq.s3.bucket_versioning.check_failed",
            next_action_hint=(
                "Ensure the S3 endpoint supports bucket versioning and that the "
                "configured credentials allow `s3:GetBucketVersioning`."
            ),
            evidence={"s3_backend_available": True, "s3_versioning_check_failed": True},
        )
    else:
        if status != "Enabled":
            result = S3BucketVersioningCheck(
                ok=False,
                status=status,
                failure_class="wopi.prereq.s3.bucket_versioning.disabled",
                next_action_hint=(
                    "Enable bucket versioning for the bucket referenced by "
                    "`AWS_STORAGE_BUCKET_NAME`. For AWS S3: "
                    "`aws s3api put-bucket-versioning --bucket <bucket> "
                    "--versioning-configuration Status=Enabled`. See "
                    "`docs/installation/backup-restore.md`."
                ),
                evidence={"s3_backend_available": True},
            )
        else:
            result = S3BucketVersioningCheck(
                ok=True,
                status="Enabled",
                evidence={"s3_backend_available": True},
            )

    cache.set(
        WOPI_S3_BUCKET_VERSIONING_CACHE_KEY,
        {
            "ok": result.ok,
            "status": result.status,
            "failure_class": result.failure_class,
            "next_action_hint": result.next_action_hint,
            "evidence": result.evidence or {},
        },
        timeout=WOPI_S3_BUCKET_VERSIONING_CACHE_TTL_SECONDS,
    )
    return result
