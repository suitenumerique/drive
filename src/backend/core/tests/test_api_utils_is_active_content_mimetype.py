"""Test utils.is_active_content_mimetype"""

from django.test import override_settings

import pytest

from core.api import utils


@pytest.mark.parametrize(
    "mimetype",
    [
        "image/svg+xml",
        "text/html",
        "application/xhtml+xml",
        "application/xml",
        "text/xml",
        "application/rss+xml",  # any +xml suffix can carry namespaced scripts or XSLT
    ],
)
def test_is_active_content_mimetype_returns_true_for_active_types(mimetype):
    """Test is_active_content_mimetype returns True for mimetypes that can run scripts"""
    assert utils.is_active_content_mimetype(mimetype) is True


def test_is_active_content_mimetype_is_case_insensitive():
    """Test is_active_content_mimetype matches the mimetype case insensitively"""
    assert utils.is_active_content_mimetype("IMAGE/SVG+XML") is True


@pytest.mark.parametrize(
    "mimetype",
    [
        "image/png",
        "image/jpeg",
        "video/mp4",
        "audio/mpeg",
        "application/json",
        "application/octet-stream",
        "text/plain",
        "text/csv",
        "application/pdf",
    ],
)
def test_is_active_content_mimetype_returns_false_for_inline_types(mimetype):
    """Test is_active_content_mimetype returns False for mimetypes allowed inline"""
    assert utils.is_active_content_mimetype(mimetype) is False


def test_is_active_content_mimetype_returns_false_when_mimetype_is_none():
    """Test is_active_content_mimetype returns False when mimetype is None"""
    assert utils.is_active_content_mimetype(None) is False


def test_is_active_content_mimetype_follows_the_setting():
    """Test the active mimetypes come from the MEDIA_ACTIVE_CONTENT_MIMETYPES setting"""
    with override_settings(MEDIA_ACTIVE_CONTENT_MIMETYPES=["application/pdf"]):
        assert utils.is_active_content_mimetype("image/svg+xml") is True
        assert utils.is_active_content_mimetype("application/pdf") is True
        # the "+xml" suffix rule is structural and always applies
        assert utils.is_active_content_mimetype("application/rss+xml") is True
