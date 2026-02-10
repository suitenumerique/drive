"""Canonical public base URL validation and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


@dataclass(frozen=True, slots=True)
class PublicUrlValidationError(ValueError):
    """Structured validation error carrying deterministic operator hints."""

    setting_name: str
    failure_class: str
    next_action_hint: str

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"{self.setting_name} validation failed. "
            f"failure_class={self.failure_class} "
            f"next_action_hint={self.next_action_hint}"
        )


def _normalize_host_port(parsed: SplitResult, *, setting_name: str) -> str:
    hostname = parsed.hostname
    if not hostname:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Set {setting_name} to an absolute URL with a host, "
                "without userinfo/query/fragment and with an empty path or '/'."
            ),
        )

    normalized_host = hostname.lower()
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"

    if parsed.port is not None:
        return f"{normalized_host}:{parsed.port}"

    return normalized_host


def normalize_public_surface_base_url(
    raw: str,
    *,
    setting_name: str,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> str:
    """
    Normalize and validate a canonical public-surface base URL without echoing the input.

    Rules:
    - absolute URL with scheme + host
    - scheme must be http/https
    - reject userinfo, query, fragment
    - restrict path to empty or '/'
    - normalize: lowercase scheme/host, remove trailing slash (path becomes empty)
    - production posture: HTTPS-only (no dev override; no mixed TLS modes)
    - non-production posture: allow HTTP only when (DEBUG==True) and allow_insecure_http==True
    """
    candidate = raw.strip()
    if not candidate:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Set {setting_name} to an absolute URL with a scheme and host "
                "(e.g. https://drive.example.com)."
            ),
        )

    parsed = urlsplit(candidate)

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Set {setting_name} to an absolute http(s) URL with a host, "
                "without userinfo/query/fragment and with an empty path or '/'."
            ),
        )

    if https_only_posture and scheme != "https":
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.https_required",
            next_action_hint=(
                f"Use https:// for {setting_name} in production (HTTPS-only). "
                "HTTP is dev-only and requires DEBUG=true and DRIVE_ALLOW_INSECURE_HTTP=true."
            ),
        )

    if scheme == "http" and not (debug and allow_insecure_http):
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.https_required",
            next_action_hint=(
                f"Use https:// for {setting_name}, or for local/dev explicitly set "
                "DRIVE_ALLOW_INSECURE_HTTP=true while running with DEBUG=true."
            ),
        )

    if parsed.username is not None or parsed.password is not None:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Remove userinfo from {setting_name} and set host/port explicitly "
                "(no username:password@...)."
            ),
        )

    if parsed.query or parsed.fragment:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Remove query/fragment from {setting_name} and keep it as a "
                "canonical base URL only."
            ),
        )

    if parsed.path not in {"", "/"}:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Remove the path from {setting_name} (it must be empty or '/')."
            ),
        )

    try:
        netloc = _normalize_host_port(parsed, setting_name=setting_name)
    except ValueError:
        raise PublicUrlValidationError(
            setting_name=setting_name,
            failure_class="config.public_url.invalid",
            next_action_hint=(
                f"Set {setting_name} to an absolute URL with a valid host/port."
            ),
        ) from None

    return urlunsplit((scheme, netloc, "", "", ""))


def normalize_drive_public_url(
    raw: str,
    *,
    https_only_posture: bool,
    debug: bool,
    allow_insecure_http: bool,
) -> str:
    """Convenience wrapper around normalize_public_surface_base_url for DRIVE_PUBLIC_URL."""
    return normalize_public_surface_base_url(
        raw,
        setting_name="DRIVE_PUBLIC_URL",
        https_only_posture=https_only_posture,
        debug=debug,
        allow_insecure_http=allow_insecure_http,
    )


def join_public_url(base_url: str, path: str) -> str:
    """
    Join a normalized canonical public base URL with an absolute path.

    The base URL is expected to be normalized (no trailing slash).
    """
    normalized_base = base_url.rstrip("/")
    if not path or path == "/":
        return normalized_base
    return f"{normalized_base}/{path.lstrip('/')}"
