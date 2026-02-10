"""Deterministic configuration preflight (no live inspection, no secrets)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand

from core.utils.public_url import (
    PublicUrlValidationError,
    normalize_public_surface_base_url,
)


@dataclass(frozen=True, slots=True)
class PreflightError:
    """Structured preflight validation error for operator-facing diagnostics."""

    field: str
    failure_class: str
    next_action_hint: str


def _normalize_required_endpoint_url(raw: str) -> None:
    candidate = (raw or "").strip()
    if not candidate:
        raise ValueError("missing")

    parsed = urlsplit(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise ValueError("invalid")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("invalid")

    if parsed.query or parsed.fragment:
        raise ValueError("invalid")

    if parsed.path not in {"", "/"}:
        raise ValueError("invalid")

    if not parsed.hostname:
        raise ValueError("invalid")


def _validate_s3_domain_replace(
    raw: str,
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> None:
    """
    Validate AWS_S3_DOMAIN_REPLACE as a public-surface base URL (EXTERNAL_BROWSER signing).

    This aligns with the centralized TLS posture rules:
    - production posture requires HTTPS (no dev override; no mixed modes)
    - dev HTTP allowed only when DEBUG=true and DRIVE_ALLOW_INSECURE_HTTP=true
    """
    try:
        normalize_public_surface_base_url(
            raw,
            setting_name="AWS_S3_DOMAIN_REPLACE",
            https_only_posture=https_only_posture,
            debug=debug,
            allow_insecure_http=allow_insecure_http,
        )
    except PublicUrlValidationError as exc:
        mapped = "config.s3.domain_replace.invalid"
        if exc.failure_class == "config.public_url.https_required":
            mapped = "config.s3.domain_replace.https_required"
        raise PublicUrlValidationError(
            setting_name="AWS_S3_DOMAIN_REPLACE",
            failure_class=mapped,
            next_action_hint=exc.next_action_hint,
        ) from None


class Command(BaseCommand):
    """Django management command emitting deterministic config + edge checklist."""

    help = "Validate edge-related config and print a proxy-agnostic checklist."

    def handle(self, *args: Any, **options: Any) -> None:
        https_only_posture = bool(getattr(settings, "SECURE_SSL_REDIRECT", False))
        debug = bool(getattr(settings, "DEBUG", False))
        allow_insecure_http = bool(
            getattr(settings, "DRIVE_ALLOW_INSECURE_HTTP", False)
        )

        errors: list[PreflightError] = []

        raw_endpoint_url = os.environ.get("AWS_S3_ENDPOINT_URL", "")
        try:
            _normalize_required_endpoint_url(raw_endpoint_url)
        except ValueError as exc:
            if str(exc) == "missing":
                errors.append(
                    PreflightError(
                        field="AWS_S3_ENDPOINT_URL",
                        failure_class="config.s3.endpoint_url.missing",
                        next_action_hint=(
                            "Set AWS_S3_ENDPOINT_URL to an absolute http(s) URL "
                            "(e.g. http://seaweedfs-s3:8333). Do not include "
                            "userinfo/query/fragment."
                        ),
                    )
                )
            else:
                errors.append(
                    PreflightError(
                        field="AWS_S3_ENDPOINT_URL",
                        failure_class="config.s3.endpoint_url.invalid",
                        next_action_hint=(
                            "Set AWS_S3_ENDPOINT_URL to an absolute http(s) URL "
                            "with a host and an empty path or '/'. Remove any "
                            "userinfo/query/fragment."
                        ),
                    )
                )

        raw_domain_replace = os.environ.get("AWS_S3_DOMAIN_REPLACE", "")
        if (raw_domain_replace or "").strip():
            try:
                _validate_s3_domain_replace(
                    raw_domain_replace,
                    https_only_posture=https_only_posture,
                    debug=debug,
                    allow_insecure_http=allow_insecure_http,
                )
            except PublicUrlValidationError as exc:
                errors.append(
                    PreflightError(
                        field="AWS_S3_DOMAIN_REPLACE",
                        failure_class=exc.failure_class,
                        next_action_hint=exc.next_action_hint,
                    )
                )

        errors_sorted = sorted(errors, key=lambda e: e.field)
        payload: dict[str, Any] = {
            "ok": len(errors_sorted) == 0,
            "errors": [asdict(e) for e in errors_sorted],
            "manual_checks": [
                {
                    "id": "edge.media.contract",
                    "audience": "INTERNAL_PROXY",
                    "title": "/media edge contract (proxy-agnostic)",
                    "expected": (
                        "Proxy forwards SigV4 headers from media-auth response "
                        "to the S3 upstream request."
                    ),
                    "required_sigv4_headers": [
                        "Authorization",
                        "X-Amz-Date",
                        "X-Amz-Content-SHA256",
                        "X-Amz-Security-Token (when present)",
                    ],
                    "routes": ["/media/", "/media/preview/", "/media-auth"],
                    "backend_media_auth_path": "/api/v1.0/items/media-auth/",
                    "no_leak": [
                        "Do not log SigV4 headers or signed URLs.",
                    ],
                },
                {
                    "id": "edge.media.signed_host_invariants",
                    "audience": "INTERNAL_PROXY+EXTERNAL_BROWSER",
                    "title": "Signed host invariants",
                    "expected": (
                        "Host used for signing must match the host seen by the "
                        "upstream request (no host rewrite that breaks SigV4)."
                    ),
                    "notes": [
                        "INTERNAL_PROXY signing uses AWS_S3_ENDPOINT_URL.",
                        "EXTERNAL_BROWSER signing uses AWS_S3_DOMAIN_REPLACE when set.",
                    ],
                },
            ],
        }

        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        if errors_sorted:
            raise SystemExit(1)
