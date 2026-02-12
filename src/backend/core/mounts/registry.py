"""Mount provider registry (bounded, deterministic)."""

from __future__ import annotations

from core.mounts.providers import static
from core.mounts.providers.base import MountProvider, MountProviderError

_PROVIDERS: dict[str, MountProvider] = {
    "static": static,
}


def get_mount_provider(provider_name: str) -> MountProvider:
    """Return a registered provider by name; raises MountProviderError if missing."""
    provider = _PROVIDERS.get((provider_name or "").strip().lower())
    if provider is None:
        raise MountProviderError(
            failure_class="mount.provider.unsupported",
            next_action_hint="Configure a supported mount provider for this mount.",
            public_message="Mount provider is not available.",
            public_code="mount.provider.unsupported",
        )
    return provider
