"""WOPI enablement + health snapshot helpers (no-leak)."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache

from wopi.tasks.configure_wopi import WOPI_CONFIGURATION_CACHE_KEY


def _sha256_16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _safe_url_host_hash(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    try:
        host = urlsplit(str(raw_url)).netloc
    except ValueError:
        return None
    host = (host or "").strip().lower()
    if not host:
        return None
    return _sha256_16(host)


@dataclass(frozen=True, slots=True)
class WopiHealth:
    """Snapshot of WOPI status with structured operator hints."""

    enabled: bool
    healthy: bool
    state: str
    failure_class: str | None = None
    next_action_hint: str | None = None
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = payload["evidence"] or {}
        return payload


def get_wopi_health() -> WopiHealth:
    """
    Compute WOPI health state without any network I/O.

    States:
    - disabled
    - enabled_healthy
    - enabled_unhealthy
    """
    clients = list(getattr(settings, "WOPI_CLIENTS", []) or [])
    enabled = bool(clients)
    if not enabled:
        return WopiHealth(
            enabled=False,
            healthy=True,
            state="disabled",
            evidence={"wopi_clients_count": 0},
        )

    evidence: dict[str, Any] = {
        "wopi_clients_count": len(clients),
        "wopi_src_base_url_host_sha256_16": _safe_url_host_hash(
            getattr(settings, "WOPI_SRC_BASE_URL", None)
        ),
        "drive_public_url_host_sha256_16": _safe_url_host_hash(
            getattr(settings, "DRIVE_PUBLIC_URL", None)
        ),
    }

    if getattr(settings, "WOPI_SRC_BASE_URL", None) is None and getattr(
        settings, "DRIVE_PUBLIC_URL", None
    ) is None:
        return WopiHealth(
            enabled=True,
            healthy=False,
            state="enabled_unhealthy",
            failure_class="wopi.config.src_base_url.missing",
            next_action_hint=(
                "Set DRIVE_PUBLIC_URL (recommended) or WOPI_SRC_BASE_URL to the "
                "canonical public base URL."
            ),
            evidence=evidence,
        )

    wopi_configuration = cache.get(WOPI_CONFIGURATION_CACHE_KEY)
    if not wopi_configuration:
        evidence.update(
            {
                "cached": False,
                "cached_mimetypes_count": 0,
                "cached_extensions_count": 0,
            }
        )
        return WopiHealth(
            enabled=True,
            healthy=False,
            state="enabled_unhealthy",
            failure_class="wopi.config.discovery.not_configured",
            next_action_hint=(
                "Run WOPI discovery configuration (celery beat) or trigger it "
                "manually with `python manage.py trigger_wopi_configuration`."
            ),
            evidence=evidence,
        )

    mimetypes = (wopi_configuration or {}).get("mimetypes") or {}
    extensions = (wopi_configuration or {}).get("extensions") or {}
    evidence.update(
        {
            "cached": True,
            "cached_mimetypes_count": len(mimetypes),
            "cached_extensions_count": len(extensions),
        }
    )

    if not mimetypes and not extensions:
        return WopiHealth(
            enabled=True,
            healthy=False,
            state="enabled_unhealthy",
            failure_class="wopi.config.discovery.empty",
            next_action_hint=(
                "Ensure WOPI discovery returns edit actions and that excluded "
                "mimetypes/extensions are not filtering everything out."
            ),
            evidence=evidence,
        )

    return WopiHealth(
        enabled=True,
        healthy=True,
        state="enabled_healthy",
        evidence=evidence,
    )

