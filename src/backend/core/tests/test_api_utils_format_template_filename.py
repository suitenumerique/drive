"""Test for the format_template_filename function in the api utils module."""

import pytest

from core.api.utils import format_template_filename


@pytest.mark.parametrize(
    "title,extension,expected",
    [
        ("my document", "odt", "my document.odt"),
        ("30/03/30 - liste à faire", "odt", "30-03-30 - liste à faire.odt"),
        ("budget/2026", "ods", "budget-2026.ods"),
        ("a/b/c/d", "odp", "a-b-c-d.odp"),
        ("/leading slash", "odt", "-leading slash.odt"),
        ("trailing slash/", "odt", "trailing slash-.odt"),
    ],
)
def test_api_utils_format_template_filename(title, extension, expected):
    assert format_template_filename(title, extension) == expected
