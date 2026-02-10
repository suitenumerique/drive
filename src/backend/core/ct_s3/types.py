"""CT-S3 typed structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .constants import Audience


@dataclass(frozen=True)
class ProviderProfile:
    """Resolved provider profile inputs for CT-S3."""

    profile_id: str
    bucket_name: str
    internal_endpoint_url: str
    external_signed_base_url: str | None


@dataclass
class CheckResult:
    """A single CT-S3 check result, keyed by (check_id, audience)."""

    check_id: str
    audience: Audience
    ok: bool
    title: str
    failure_class: str | None = None
    next_action_hint: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunnerOptions:
    """Runner options that influence strictness or IO behavior."""

    strict_range_206: bool = False
    http_timeout_s: float = 10.0
