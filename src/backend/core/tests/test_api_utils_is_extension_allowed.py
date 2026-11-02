"""Test for the is_extension_allowed function in the api utils module."""

import pytest

from core.api.utils import is_extension_allowed


def test_api_utils_is_extension_allowed_unknown_mode(settings):
    """An unknown RESTRICT_UPLOAD_FILE_TYPE should raise instead of allowing the file."""
    settings.RESTRICT_UPLOAD_FILE_TYPE = "deny"

    with pytest.raises(ValueError, match="Unknown RESTRICT_UPLOAD_FILE_TYPE 'deny'"):
        is_extension_allowed("file.exe")
