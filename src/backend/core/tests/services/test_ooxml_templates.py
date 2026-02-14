"""Tests for minimal OOXML template generation."""

from io import BytesIO
from zipfile import ZipFile

import pytest

from core.services.ooxml_templates import build_minimal_ooxml_template_bytes


@pytest.mark.parametrize(
    ("ext", "expected_paths"),
    [
        (
            "docx",
            {
                "[Content_Types].xml",
                "_rels/.rels",
                "word/document.xml",
            },
        ),
        (
            "xlsx",
            {
                "[Content_Types].xml",
                "_rels/.rels",
                "xl/workbook.xml",
                "xl/worksheets/sheet1.xml",
            },
        ),
        (
            "pptx",
            {
                "[Content_Types].xml",
                "_rels/.rels",
                "ppt/presentation.xml",
                "ppt/slides/slide1.xml",
            },
        ),
    ],
)
def test_build_minimal_ooxml_template_bytes_builds_zip_with_core_parts(
    ext,
    expected_paths,
):
    mimetype, payload = build_minimal_ooxml_template_bytes(ext)
    assert mimetype
    assert payload[:2] == b"PK"

    with ZipFile(BytesIO(payload)) as zf:
        names = set(zf.namelist())

    assert expected_paths.issubset(names)


def test_build_minimal_ooxml_template_bytes_rejects_unknown_extension():
    with pytest.raises(ValueError, match="unsupported_extension"):
        build_minimal_ooxml_template_bytes("unknown")
