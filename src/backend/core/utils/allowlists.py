"""Deterministic allowlist validation/normalization helpers (no wildcards, no-leak)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit

from core.utils.public_url import (
    PublicUrlValidationError,
    normalize_public_surface_base_url,
)


@dataclass(frozen=True, slots=True)
class AllowlistValidationError(ValueError):
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


@dataclass(frozen=True, slots=True)
class TlsPosture:
    """TLS posture for allowlist validation."""

    https_only_posture: bool
    debug: bool
    allow_insecure_http: bool


def _reject_wildcards(candidate: str, *, setting_name: str, kind: str) -> None:
    if "*" in candidate:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class=f"config.allowlist.{kind}.wildcard",
            next_action_hint="Remove wildcards; provide explicit values only.",
        )


def _normalize_host_port(parsed: SplitResult, *, setting_name: str, kind: str) -> str:
    hostname = parsed.hostname
    if not hostname:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class=f"config.allowlist.{kind}.invalid",
            next_action_hint="Provide an absolute URL with a valid host/port.",
        )

    normalized_host = hostname.lower()
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"

    if parsed.port is not None:
        return f"{normalized_host}:{parsed.port}"

    return normalized_host


def _enforce_http_policy(
    *,
    scheme: str,
    posture: TlsPosture,
    setting_name: str,
    kind: str,
) -> None:
    if posture.https_only_posture and scheme != "https":
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class=f"config.allowlist.{kind}.https_required",
            next_action_hint=(
                f"Use https:// for {setting_name} in production (HTTPS-only). "
                "HTTP is dev-only and requires DEBUG=true and DRIVE_ALLOW_INSECURE_HTTP=true."
            ),
        )

    if scheme == "http" and not (posture.debug and posture.allow_insecure_http):
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class=f"config.allowlist.{kind}.https_required",
            next_action_hint=(
                f"Use https:// for {setting_name}, or for local/dev explicitly set "
                "DRIVE_ALLOW_INSECURE_HTTP=true while running with DEBUG=true."
            ),
        )


def normalize_allowlisted_redirect_uri(
    raw: str,
    *,
    setting_name: str,
    posture: TlsPosture,
) -> str:
    """
    Redirect URIs are absolute URIs (scheme + host + path).

    No wildcards, no query/fragment/userinfo. Path is normalized to be at least '/'.
    """
    candidate = str(raw).strip()
    if not candidate:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.redirect_uri.invalid",
            next_action_hint="Provide an absolute URI with scheme + host + path.",
        )

    _reject_wildcards(candidate, setting_name=setting_name, kind="redirect_uri")

    parsed = urlsplit(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.redirect_uri.invalid",
            next_action_hint="Provide an absolute http(s) URI with scheme + host + path.",
        )

    _enforce_http_policy(
        scheme=scheme,
        posture=posture,
        setting_name=setting_name,
        kind="redirect_uri",
    )

    if parsed.username is not None or parsed.password is not None:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.redirect_uri.invalid",
            next_action_hint="Remove userinfo from redirect URIs (no username:password@...).",
        )

    if parsed.query or parsed.fragment:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.redirect_uri.invalid",
            next_action_hint="Remove query/fragment from redirect URIs; keep them canonical.",
        )

    netloc = _normalize_host_port(
        parsed, setting_name=setting_name, kind="redirect_uri"
    )
    path = parsed.path or "/"
    if not path.startswith("/"):
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.redirect_uri.invalid",
            next_action_hint="Redirect URI path must start with '/'.",
        )

    normalized_path = "/" + path.lstrip("/")

    return urlunsplit((scheme, netloc, normalized_path, "", ""))


def normalize_allowlisted_origin(
    raw: str,
    *,
    setting_name: str,
    posture: TlsPosture,
) -> str:
    """Origins are scheme+host(+port) only (no path/query/fragment)."""
    candidate = str(raw).strip()
    if not candidate:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.origin.invalid",
            next_action_hint="Provide an origin as scheme://host[:port] (no path/query/fragment).",
        )

    _reject_wildcards(candidate, setting_name=setting_name, kind="origin")

    try:
        normalized = normalize_public_surface_base_url(
            candidate,
            setting_name=setting_name,
            https_only_posture=posture.https_only_posture,
            debug=posture.debug,
            allow_insecure_http=posture.allow_insecure_http,
        )
    except PublicUrlValidationError as exc:
        mapped = (
            "config.allowlist.origin.https_required"
            if exc.failure_class.endswith("https_required")
            else "config.allowlist.origin.invalid"
        )
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class=mapped,
            next_action_hint=exc.next_action_hint,
        ) from None

    return normalized


def normalize_allowlisted_host(raw: str, *, setting_name: str) -> str:
    """Hosts are hostnames (optionally with explicit port). No scheme/path/query/fragment."""
    candidate = str(raw).strip()
    if not candidate:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.host.invalid",
            next_action_hint="Provide a hostname (optionally with :port), without scheme/path.",
        )

    _reject_wildcards(candidate, setting_name=setting_name, kind="host")

    if "://" in candidate or "/" in candidate or "?" in candidate or "#" in candidate:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.host.invalid",
            next_action_hint="Provide hostnames only (no scheme/path/query/fragment).",
        )

    parsed = urlsplit(f"//{candidate}")
    if parsed.username is not None or parsed.password is not None:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.host.invalid",
            next_action_hint="Remove userinfo; provide host[:port] only.",
        )

    if parsed.path or parsed.query or parsed.fragment:
        raise AllowlistValidationError(
            setting_name=setting_name,
            failure_class="config.allowlist.host.invalid",
            next_action_hint="Provide host[:port] only, without extra components.",
        )

    return _normalize_host_port(parsed, setting_name=setting_name, kind="host")


def extract_host_from_url_form(
    raw: str,
    *,
    setting_name: str,
    posture: TlsPosture,
) -> str:
    """Normalize an origin URL (scheme+host) and return its netloc (host[:port])."""
    normalized_origin = normalize_allowlisted_origin(
        raw,
        setting_name=setting_name,
        posture=posture,
    )
    return urlsplit(normalized_origin).netloc


def dedupe_sorted(*values: str) -> list[str]:
    """Deterministic unique list (sorted)."""
    return sorted({v for v in values if v})


def merge_allowlist(canonical: list[str], additions: list[str]) -> list[str]:
    """Canonical entries first, additions sorted, then deduped deterministically."""
    merged: list[str] = []
    seen: set[str] = set()
    for item in canonical + sorted(additions):
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged
