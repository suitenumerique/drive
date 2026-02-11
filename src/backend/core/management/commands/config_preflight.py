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


def _normalize_required_absolute_url(
    raw: str,
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> None:
    """
    Validate a required absolute http(s) URL (allowing paths) without echoing the input.

    Rules:
    - absolute URL with scheme + host
    - scheme must be http/https
    - reject userinfo, query, fragment
    - HTTPS-only posture: require https
    - non-production: allow http only when DEBUG=true and DRIVE_ALLOW_INSECURE_HTTP=true
    """
    candidate = (raw or "").strip()
    if not candidate:
        raise ValueError("missing")

    parsed = urlsplit(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise ValueError("invalid")

    if https_only_posture and scheme != "https":
        raise ValueError("https_required")

    if scheme == "http" and not (debug and allow_insecure_http):
        raise ValueError("https_required")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("invalid")

    if parsed.query or parsed.fragment:
        raise ValueError("invalid")

    if not parsed.hostname:
        raise ValueError("invalid")


def _validate_oidc_secret_ref() -> None:
    """
    Validate OIDC client secret is refs-only.

    Accepted (file takes precedence):
    - OIDC_RP_CLIENT_SECRET_FILE=/path/to/file
    - OIDC_RP_CLIENT_SECRET_ENV=SOME_ENV_VAR_NAME (and SOME_ENV_VAR_NAME is set)
    """
    if (os.environ.get("OIDC_RP_CLIENT_SECRET") or "").strip():
        raise ValueError("direct_forbidden")

    file_ref = (os.environ.get("OIDC_RP_CLIENT_SECRET_FILE") or "").strip()
    env_ref = (os.environ.get("OIDC_RP_CLIENT_SECRET_ENV") or "").strip()

    if file_ref:
        if not os.path.exists(file_ref):
            raise ValueError("file_missing")
        try:
            with open(file_ref, encoding="utf-8") as file:
                _ = file.read(1)
        except (OSError, PermissionError) as err:
            raise ValueError("file_unreadable") from err
        return

    if env_ref:
        ref_value = (os.environ.get(env_ref) or "").strip()
        if not ref_value:
            raise ValueError("env_ref_missing")
        return

    raise ValueError("missing")


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


def _validate_s3_preflight(
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> list[PreflightError]:
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

    return errors


def _validate_oidc_preflight(
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> list[PreflightError]:
    errors: list[PreflightError] = []
    errors.extend(
        _validate_oidc_endpoint_fields(
            https_only_posture=https_only_posture,
            debug=debug,
            allow_insecure_http=allow_insecure_http,
        )
    )
    errors.extend(
        _validate_oidc_op_url_field(
            https_only_posture=https_only_posture,
            debug=debug,
            allow_insecure_http=allow_insecure_http,
        )
    )
    errors.extend(_validate_oidc_client_id_field())
    errors.extend(_validate_oidc_secret_ref_field())
    return errors


def _validate_oidc_endpoint_fields(
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> list[PreflightError]:
    errors: list[PreflightError] = []
    oidc_fields = [
        "OIDC_OP_AUTHORIZATION_ENDPOINT",
        "OIDC_OP_JWKS_ENDPOINT",
        "OIDC_OP_TOKEN_ENDPOINT",
        "OIDC_OP_USER_ENDPOINT",
    ]

    for field in oidc_fields:
        raw = os.environ.get(field, "")
        try:
            _normalize_required_absolute_url(
                raw,
                https_only_posture=https_only_posture,
                debug=debug,
                allow_insecure_http=allow_insecure_http,
            )
        except ValueError as exc:
            reason = str(exc)
            if reason == "missing":
                errors.append(
                    PreflightError(
                        field=field,
                        failure_class="config.oidc.endpoint_url.missing",
                        next_action_hint=(
                            f"Set {field} to an absolute http(s) URL. "
                            "Do not include userinfo/query/fragment."
                        ),
                    )
                )
            elif reason == "https_required":
                errors.append(
                    PreflightError(
                        field=field,
                        failure_class="config.oidc.endpoint_url.https_required",
                        next_action_hint=(
                            f"Use https:// for {field} in production (HTTPS-only). "
                            "HTTP is dev-only and requires DEBUG=true and "
                            "DRIVE_ALLOW_INSECURE_HTTP=true."
                        ),
                    )
                )
            else:
                errors.append(
                    PreflightError(
                        field=field,
                        failure_class="config.oidc.endpoint_url.invalid",
                        next_action_hint=(
                            f"Set {field} to an absolute http(s) URL with a host. "
                            "Remove userinfo/query/fragment."
                        ),
                    )
                )

    return errors


def _validate_oidc_op_url_field(
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> list[PreflightError]:
    raw_op_url = os.environ.get("OIDC_OP_URL", "")
    if not (raw_op_url or "").strip():
        return []

    try:
        _normalize_required_absolute_url(
            raw_op_url,
            https_only_posture=https_only_posture,
            debug=debug,
            allow_insecure_http=allow_insecure_http,
        )
    except ValueError as exc:
        if str(exc) == "https_required":
            return [
                PreflightError(
                    field="OIDC_OP_URL",
                    failure_class="config.oidc.op_url.https_required",
                    next_action_hint=(
                        "Use https:// for OIDC_OP_URL in production (HTTPS-only). "
                        "HTTP is dev-only and requires DEBUG=true and "
                        "DRIVE_ALLOW_INSECURE_HTTP=true."
                    ),
                )
            ]
        return [
            PreflightError(
                field="OIDC_OP_URL",
                failure_class="config.oidc.op_url.invalid",
                next_action_hint=(
                    "Set OIDC_OP_URL to an absolute http(s) URL with a host. "
                    "Remove userinfo/query/fragment."
                ),
            )
        ]

    return []


def _validate_oidc_client_id_field() -> list[PreflightError]:
    raw_client_id = os.environ.get("OIDC_RP_CLIENT_ID", "")
    if (raw_client_id or "").strip():
        return []
    return [
        PreflightError(
            field="OIDC_RP_CLIENT_ID",
            failure_class="config.oidc.client_id.missing",
            next_action_hint="Set OIDC_RP_CLIENT_ID to your OIDC client id.",
        )
    ]


def _validate_oidc_secret_ref_field() -> list[PreflightError]:
    try:
        _validate_oidc_secret_ref()
        return []
    except ValueError as exc:
        reason = str(exc)
        if reason == "direct_forbidden":
            return [
                PreflightError(
                    field="OIDC_RP_CLIENT_SECRET",
                    failure_class="config.oidc.client_secret.direct_value_forbidden",
                    next_action_hint=(
                        "Do not set OIDC_RP_CLIENT_SECRET directly. "
                        "Use OIDC_RP_CLIENT_SECRET_FILE or OIDC_RP_CLIENT_SECRET_ENV."
                    ),
                )
            ]
        if reason == "file_missing":
            return [
                PreflightError(
                    field="OIDC_RP_CLIENT_SECRET_FILE",
                    failure_class="config.oidc.client_secret.file_missing",
                    next_action_hint=(
                        "Ensure OIDC_RP_CLIENT_SECRET_FILE points to an existing file."
                    ),
                )
            ]
        if reason == "file_unreadable":
            return [
                PreflightError(
                    field="OIDC_RP_CLIENT_SECRET_FILE",
                    failure_class="config.oidc.client_secret.file_unreadable",
                    next_action_hint=(
                        "Ensure OIDC_RP_CLIENT_SECRET_FILE is readable by the process."
                    ),
                )
            ]
        if reason == "env_ref_missing":
            return [
                PreflightError(
                    field="OIDC_RP_CLIENT_SECRET_ENV",
                    failure_class="config.oidc.client_secret.env_ref_missing",
                    next_action_hint=(
                        "Ensure OIDC_RP_CLIENT_SECRET_ENV references a set env var."
                    ),
                )
            ]
        return [
            PreflightError(
                field="OIDC_RP_CLIENT_SECRET",
                failure_class="config.oidc.client_secret.missing",
                next_action_hint=(
                    "Set OIDC_RP_CLIENT_SECRET_FILE or OIDC_RP_CLIENT_SECRET_ENV."
                ),
            )
        ]


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
        errors.extend(
            _validate_s3_preflight(
                https_only_posture=https_only_posture,
                debug=debug,
                allow_insecure_http=allow_insecure_http,
            )
        )
        errors.extend(
            _validate_oidc_preflight(
                https_only_posture=https_only_posture,
                debug=debug,
                allow_insecure_http=allow_insecure_http,
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
