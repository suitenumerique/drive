"""Tests for mounts registry deterministic validation."""

import pytest

from core.services.mounts_registry import (
    MountRegistryValidationError,
    validate_mounts_registry,
)


def test_validate_mounts_registry_sorts_and_normalizes_provider():
    """Valid mounts are sorted and providers are normalized."""
    mounts = validate_mounts_registry(
        [
            {
                "mount_id": "beta-mount",
                "display_name": "Beta",
                "provider": "SMB",
                "enabled": True,
                "params": {"host": "smb.internal"},
            },
            {
                "mount_id": "alpha-mount",
                "display_name": "Alpha",
                "provider": "smb",
                "enabled": True,
                "params": {},
            },
        ]
    )
    assert [m["mount_id"] for m in mounts] == ["alpha-mount", "beta-mount"]
    assert mounts[1]["provider"] == "smb"


def test_validate_mounts_registry_rejects_duplicate_mount_id():
    """Duplicate mount_id values are rejected deterministically."""
    with pytest.raises(MountRegistryValidationError) as excinfo:
        validate_mounts_registry(
            [
                {
                    "mount_id": "alpha-mount",
                    "display_name": "Alpha",
                    "provider": "smb",
                    "enabled": True,
                    "params": {},
                },
                {
                    "mount_id": "alpha-mount",
                    "display_name": "Alpha2",
                    "provider": "smb",
                    "enabled": True,
                    "params": {},
                },
            ]
        )
    assert excinfo.value.failure_class == "mount.config.mount_id.duplicate"
