"""Tests for the quota_to_str helper."""

import pytest

from core.entitlements.backends.base import QuotaError, QuotaReason, QuotaState
from core.utils.quota import quota_to_str


@pytest.mark.parametrize(
    "quota,expected",
    [
        ({}, "No quota"),
        (
            {"state": QuotaState.DEFAULT, "usage": 250, "limit": 1000},
            "State: default\nUsage: 250 B\nLimit: 1.00 KB\nUsed: 25 %",
        ),
        # A limit of zero must not be used to compute a percentage
        (
            {"state": QuotaState.DEFAULT, "usage": 250, "limit": 0},
            "State: default\nUsage: 250 B\nLimit: 0.00 B",
        ),
        (
            {
                "state": QuotaState.EXCEEDED_LOCKED,
                "reason": QuotaReason.ORGANIZATION_QUOTA_EXCEEDED,
            },
            "State: exceeded_locked\nReason: organization_quota_exceeded",
        ),
        (
            {"state": QuotaState.ERROR, "error": QuotaError.METRIC_ACCOUNT_NOT_FOUND},
            "State: error\nError: metric_account_not_found",
        ),
    ],
)
def test_utils_quota_to_str(quota, expected):
    """Every field of the quota should be shown on its own labelled line."""
    assert quota_to_str(quota) == expected
