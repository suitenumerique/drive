"""MountProvider base contracts."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Literal, Protocol

EntryType = Literal["file", "folder"]


@dataclasses.dataclass(frozen=True, slots=True)
class MountEntry:
    """Provider-agnostic mount entry (contract-level)."""

    entry_type: EntryType
    normalized_path: str
    name: str
    size: int | None = None
    modified_at: datetime | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class MountProviderError(Exception):
    """Deterministic provider error (no-leak) with guidance."""

    failure_class: str
    next_action_hint: str
    public_message: str
    public_code: str


class MountProvider(Protocol):
    """Mount provider contract (v1: browse only)."""

    def stat(self, *, mount: dict, normalized_path: str) -> MountEntry:
        """Return metadata for the target path; raises MountProviderError."""

    def list_children(self, *, mount: dict, normalized_path: str) -> list[MountEntry]:
        """List immediate children entries for a folder path; raises MountProviderError."""
