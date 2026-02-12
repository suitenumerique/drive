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
                "params": {
                    "server": "smb.internal",
                    "share": "finance",
                    "username": "svc",
                },
            },
            {
                "mount_id": "alpha-mount",
                "display_name": "Alpha",
                "provider": "smb",
                "enabled": True,
                "params": {
                    "server": "smb.internal",
                    "share": "finance",
                    "username": "svc",
                },
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
                    "params": {
                        "server": "smb.internal",
                        "share": "finance",
                        "username": "svc",
                    },
                },
                {
                    "mount_id": "alpha-mount",
                    "display_name": "Alpha2",
                    "provider": "smb",
                    "enabled": True,
                    "params": {
                        "server": "smb.internal",
                        "share": "finance",
                        "username": "svc",
                    },
                },
            ]
        )
    assert excinfo.value.failure_class == "mount.config.mount_id.duplicate"


def test_validate_mounts_registry_smb_requires_server_share_username():
    """SMB mounts validate required fields deterministically."""
    with pytest.raises(MountRegistryValidationError) as excinfo:
        validate_mounts_registry(
            [
                {
                    "mount_id": "alpha-mount",
                    "display_name": "Alpha",
                    "provider": "smb",
                    "enabled": True,
                    "params": {"share": "finance", "username": "svc"},
                }
            ]
        )
    assert excinfo.value.failure_class == "mount.config.smb.server.missing"


def test_validate_mounts_registry_smb_port_defaults_and_is_validated():
    """SMB port defaults to 445 and rejects invalid types deterministically."""
    mounts = validate_mounts_registry(
        [
            {
                "mount_id": "alpha-mount",
                "display_name": "Alpha",
                "provider": "smb",
                "enabled": True,
                "params": {
                    "server": "smb.internal",
                    "share": "finance",
                    "username": "svc",
                },
            }
        ]
    )
    assert mounts[0]["params"]["port"] == 445

    with pytest.raises(MountRegistryValidationError) as excinfo:
        validate_mounts_registry(
            [
                {
                    "mount_id": "alpha-mount",
                    "display_name": "Alpha",
                    "provider": "smb",
                    "enabled": True,
                    "params": {
                        "server": "smb.internal",
                        "share": "finance",
                        "username": "svc",
                        "port": "445",
                    },
                }
            ]
        )
    assert excinfo.value.failure_class == "mount.config.smb.port.invalid_type"


def test_validate_mounts_registry_rejects_direct_password_values():
    """Direct password values are forbidden (refs-only)."""
    with pytest.raises(MountRegistryValidationError) as excinfo:
        validate_mounts_registry(
            [
                {
                    "mount_id": "alpha-mount",
                    "display_name": "Alpha",
                    "provider": "smb",
                    "enabled": True,
                    "password": "secret",
                    "params": {
                        "server": "smb.internal",
                        "share": "finance",
                        "username": "svc",
                    },
                }
            ]
        )
    assert excinfo.value.failure_class == "mount.config.secrets.direct_value_forbidden"
