"""Tests for the format_size helper."""

import pytest

from core.utils.sizes import format_size


# Same cases as the frontend formatSize tests, keep them in sync
@pytest.mark.parametrize(
    "size,expected",
    [
        (0, "0.00 B"),
        (999, "999 B"),
        (1000, "1.00 KB"),
        (9_994, "9.99 KB"),
        (10_000, "10.0 KB"),
        (99_940, "99.9 KB"),
        (100_500, "101 KB"),
        (999_999, "1000 KB"),
        (3_631_743_364, "3.63 GB"),
        (15_000_000_000, "15.0 GB"),
        (155_800_000, "156 MB"),
        (10**18, "1000 PB"),
    ],
)
def test_utils_format_size(size, expected):
    """Sizes should be formatted with decimal units and the frontend rounding."""
    assert format_size(size) == expected
