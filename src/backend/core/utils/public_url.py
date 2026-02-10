"""Canonical public base URL validation and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


@dataclass(frozen=True, slots=True)
class PublicUrlValidationError(ValueError):
    """Structured validation error carrying deterministic operator hints."""

    failure_class: str
    next_action_hint: str

    def __str__(self) -> str:  # pragma: no cover
        return (
            "DRIVE_PUBLIC_URL validation failed. "
            f"failure_class={self.failure_class} "
            f"next_action_hint={self.next_action_hint}"
        )


def _normalize_host_port(parsed: SplitResult) -> str:
    hostname = parsed.hostname
    if not hostname:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Set DRIVE_PUBLIC_URL to an absolute URL with a host, "
                "without userinfo/query/fragment and with an empty path or '/'."
            ),
        )

    normalized_host = hostname.lower()
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"

    if parsed.port is not None:
        return f"{normalized_host}:{parsed.port}"

    return normalized_host


def normalize_drive_public_url(
    raw: str,
    *,
    production_posture: bool,
    allow_insecure_http: bool,
) -> str:
    """
    Normalize and validate DRIVE_PUBLIC_URL without echoing the input value.

    Rules:
    - absolute URL with scheme + host
    - scheme must be http/https
    - reject userinfo, query, fragment
    - restrict path to empty or '/'
    - normalize: lowercase scheme/host, remove trailing slash (path becomes empty)
    - enforce https in production posture unless allow_insecure_http is true
    """
    candidate = raw.strip()
    if not candidate:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Set DRIVE_PUBLIC_URL to an absolute URL with a scheme and host "
                "(e.g. https://drive.example.com)."
            ),
        )

    parsed = urlsplit(candidate)

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Set DRIVE_PUBLIC_URL to an absolute http(s) URL with a host, "
                "without userinfo/query/fragment and with an empty path or '/'."
            ),
        )

    if production_posture and scheme != "https" and not allow_insecure_http:
        raise PublicUrlValidationError(
            failure_class="config.public_url.https_required",
            next_action_hint=(
                "Use https:// for DRIVE_PUBLIC_URL in production, or explicitly set "
                "DRIVE_ALLOW_INSECURE_HTTP=true for local/dev-only overrides."
            ),
        )

    if parsed.username is not None or parsed.password is not None:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Remove userinfo from DRIVE_PUBLIC_URL and set host/port explicitly "
                "(no username:password@...)."
            ),
        )

    if parsed.query or parsed.fragment:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Remove query/fragment from DRIVE_PUBLIC_URL and keep it as a "
                "canonical base URL only."
            ),
        )

    if parsed.path not in {"", "/"}:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Remove the path from DRIVE_PUBLIC_URL (it must be empty or '/')."
            ),
        )

    try:
        netloc = _normalize_host_port(parsed)
    except ValueError:
        raise PublicUrlValidationError(
            failure_class="config.public_url.invalid",
            next_action_hint=(
                "Set DRIVE_PUBLIC_URL to an absolute URL with a valid host/port."
            ),
        ) from None

    return urlunsplit((scheme, netloc, "", "", ""))
