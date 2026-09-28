"""Tests for the conversion policy helpers."""

from django.conf import settings

from core import factories
from wopi.conversion.policy import is_forced_conversion, target_extension_for


def _item(filename="document.doc", mimetype="application/msword"):
    """Build a minimal in-memory Item for policy tests."""
    return factories.ItemFactory.build(filename=filename, mimetype=mimetype)


def test_target_extension_for_known_legacy_formats():
    """Map known legacy Office extensions to their modern equivalents."""
    assert target_extension_for("doc") == "docx"
    assert target_extension_for("xls") == "xlsx"
    assert target_extension_for("ppt") == "pptx"


def test_target_extension_for_unknown_format_returns_none():
    """Return None for unsupported or empty source extensions."""
    assert target_extension_for("docx") is None
    assert target_extension_for("") is None
    assert target_extension_for(None) is None


def test_target_extension_for_is_case_insensitive():
    """Match the target extension regardless of source extension case."""
    assert target_extension_for("DOC") == "docx"
    assert target_extension_for("Xls") == "xlsx"


def test_legacy_conversion_targets_only_lists_legacy_formats():
    """Restrict the conversion policy to legacy Office formats."""
    assert set(settings.WOPI_LEGACY_CONVERSION_TARGETS) == {"doc", "xls", "ppt"}


def test_is_forced_conversion_true_when_extension_listed():
    """Force conversion when the item extension is listed."""
    options = {"ForceConvertExtensions": ["doc", "xls", "ppt"]}
    assert is_forced_conversion(_item(filename="document.doc"), options) is True


def test_is_forced_conversion_true_when_mimetype_listed():
    """Force conversion when the item mimetype is listed."""
    options = {"ForceConvertMimetypes": ["application/msword"]}
    item = _item(filename="document.unknown", mimetype="application/msword")
    assert is_forced_conversion(item, options) is True


def test_is_forced_conversion_false_when_neither_matches():
    """Skip conversion when neither extension nor mimetype matches."""
    options = {
        "ForceConvertExtensions": ["doc"],
        "ForceConvertMimetypes": ["application/msword"],
    }
    item = _item(filename="document.docx", mimetype="application/vnd.openxmlformats")
    assert is_forced_conversion(item, options) is False


def test_is_forced_conversion_false_when_options_missing():
    """Skip conversion when client options are missing."""
    assert is_forced_conversion(_item(), {}) is False
    assert is_forced_conversion(_item(), None) is False


def test_is_forced_conversion_extension_check_is_case_insensitive():
    """Match forced extensions regardless of case."""
    options = {"ForceConvertExtensions": ["doc"]}
    assert is_forced_conversion(_item(filename="REPORT.DOC"), options) is True

    options = {"ForceConvertExtensions": ["DOC"]}
    assert is_forced_conversion(_item(filename="document.doc"), options) is True
