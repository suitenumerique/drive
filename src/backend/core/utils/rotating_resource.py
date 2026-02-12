"""Version-bound resource reuse to avoid stale credentials after rotation."""

from __future__ import annotations

import dataclasses
import threading
from typing import Callable, Generic, TypedDict, TypeVar

CredentialsT = TypeVar("CredentialsT")
ResourceT = TypeVar("ResourceT")


class RotatingResourceEvidence(TypedDict, total=False):
    """Allow-listed, no-leak evidence for operator-facing diagnostics."""

    credential_version: str


@dataclasses.dataclass(frozen=True, slots=True)
class RotatingResourceError(Exception):
    """Deterministic, no-leak error for version-bound resource creation."""

    failure_class: str
    next_action_hint: str
    safe_evidence: RotatingResourceEvidence
    public_message: str = "Connection/session initialization failed."
    public_code: str = "mount.session.init_failed"


class RotatingResource(Generic[CredentialsT, ResourceT]):
    """
    Safely reuse a pooled resource while preventing stale-credential reuse.

    The caller supplies a `credentials_provider` that returns:
    - credentials (may be sensitive; never stored), and
    - a stable `version` string that changes when credentials rotate.

    On each `get()`, the current version is checked. If it differs from the
    cached version, a new resource is created and returned; stale resources are
    never returned for new operations after rotation is observed.
    """

    def __init__(
        self,
        *,
        credentials_provider: Callable[[], tuple[CredentialsT, str]],
        factory: Callable[[CredentialsT], ResourceT],
    ) -> None:
        """Create a rotating resource wrapper."""

        self._credentials_provider = credentials_provider
        self._factory = factory
        self._lock = threading.Lock()
        self._resource: ResourceT | None = None
        self._version: str | None = None

    def get(self) -> ResourceT:
        """
        Return a pooled resource bound to the current credential version.

        If the credential version changed since the previous call, a new
        resource is created.
        """

        credentials, version = self._credentials_provider()
        with self._lock:
            if self._resource is not None and self._version == version:
                return self._resource

            try:
                resource = self._factory(credentials)
            except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
                raise RotatingResourceError(
                    failure_class="mount.session.init_failed",
                    next_action_hint=(
                        "Inspect provider connection settings and secret resolution, "
                        "then retry the operation."
                    ),
                    safe_evidence={"credential_version": str(version)},
                ) from None

            self._resource = resource
            self._version = version
            return resource
