"""CT-S3 constants (audiences, gate ids, and check ids)."""

from __future__ import annotations

from typing import Literal

Audience = Literal["INTERNAL_PROXY", "EXTERNAL_BROWSER"]

AUDIENCE_INTERNAL_PROXY: Audience = "INTERNAL_PROXY"
AUDIENCE_EXTERNAL_BROWSER: Audience = "EXTERNAL_BROWSER"

CT_S3_GATE_PREFIX = "s3.contracts"

# Provider profile ids (stable)
PROFILE_SEAWEEDFS_S3 = "seaweedfs-s3"
