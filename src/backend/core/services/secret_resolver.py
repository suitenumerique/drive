"""Singleton secret resolver(s) for runtime secret resolution (mount providers)."""

from __future__ import annotations

from functools import lru_cache

from django.conf import settings

from core.utils.secret_resolver import SecretResolver


@lru_cache(maxsize=1)
def get_mount_secret_resolver() -> SecretResolver:
    refresh_seconds = int(getattr(settings, "MOUNTS_SECRET_REFRESH_SECONDS", 60) or 60)
    if refresh_seconds < 1:
        refresh_seconds = 1
    return SecretResolver(refresh_seconds=refresh_seconds)

