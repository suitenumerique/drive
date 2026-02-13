"""Minimal ODF (OpenDocument) templates for WOPI-compatible new documents.

We intentionally generate templates in code to avoid shipping binary assets and
to ensure we never create 0-byte .odt/.ods/.odp files (ODF is a zip container).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


@dataclass(frozen=True, slots=True)
class OdfTemplateSpec:
    extension: str
    mimetype: str
    content_xml: str


_ODF_TEMPLATES: dict[str, OdfTemplateSpec] = {
    "odt": OdfTemplateSpec(
        extension="odt",
        mimetype="application/vnd.oasis.opendocument.text",
        content_xml=(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<office:document-content "
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
            'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
            'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
            'xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" '
            'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
            'office:version="1.3">\n'
            "  <office:body>\n"
            "    <office:text>\n"
            "      <text:p/>\n"
            "    </office:text>\n"
            "  </office:body>\n"
            "</office:document-content>\n"
        ),
    ),
    "ods": OdfTemplateSpec(
        extension="ods",
        mimetype="application/vnd.oasis.opendocument.spreadsheet",
        content_xml=(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<office:document-content "
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
            'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
            'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
            'office:version="1.3">\n'
            "  <office:body>\n"
            "    <office:spreadsheet>\n"
            '      <table:table table:name="Sheet1">\n'
            "        <table:table-row>\n"
            "          <table:table-cell>\n"
            "            <text:p/>\n"
            "          </table:table-cell>\n"
            "        </table:table-row>\n"
            "      </table:table>\n"
            "    </office:spreadsheet>\n"
            "  </office:body>\n"
            "</office:document-content>\n"
        ),
    ),
    "odp": OdfTemplateSpec(
        extension="odp",
        mimetype="application/vnd.oasis.opendocument.presentation",
        content_xml=(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<office:document-content "
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
            'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
            'office:version="1.3">\n'
            "  <office:body>\n"
            "    <office:presentation>\n"
            '      <draw:page draw:name="page1" '
            'draw:style-name="dp1" draw:master-page-name="Default">\n'
            "        <presentation:notes/>\n"
            "      </draw:page>\n"
            "    </office:presentation>\n"
            "  </office:body>\n"
            "</office:document-content>\n"
        ),
    ),
}


def _manifest_xml(mimetype: str) -> str:
    # Keep this minimal and deterministic.
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<manifest:manifest "
        'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.3">\n'
        f'  <manifest:file-entry manifest:full-path="/" manifest:media-type="{mimetype}"/>\n'
        '  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>\n'
        '  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>\n'
        '  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>\n'
        '  <manifest:file-entry manifest:full-path="settings.xml" manifest:media-type="text/xml"/>\n'
        "</manifest:manifest>\n"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<office:document-styles "
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
        'office:version="1.3">\n'
        "  <office:styles/>\n"
        "  <office:automatic-styles/>\n"
        "  <office:master-styles/>\n"
        "</office:document-styles>\n"
    )


def _meta_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<office:document-meta "
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'office:version="1.3">\n'
        "  <office:meta>\n"
        "    <meta:generator>Drive</meta:generator>\n"
        "  </office:meta>\n"
        "</office:document-meta>\n"
    )


def _settings_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<office:document-settings "
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'office:version="1.3">\n'
        "  <office:settings/>\n"
        "</office:document-settings>\n"
    )


def build_minimal_odf_template_bytes(kind: str) -> tuple[str, bytes]:
    """
    Build a minimal, valid ODF template for the requested kind.

    Returns (mimetype, bytes).
    """
    spec = _ODF_TEMPLATES.get(str(kind or "").strip().lower())
    if spec is None:
        raise ValueError("unsupported_kind")

    buffer = BytesIO()
    with ZipFile(buffer, mode="w") as zf:
        # Per ODF packaging rules: the mimetype file must be first and uncompressed.
        zf.writestr("mimetype", spec.mimetype, compress_type=ZIP_STORED)
        zf.writestr("content.xml", spec.content_xml, compress_type=ZIP_DEFLATED)
        zf.writestr("styles.xml", _styles_xml(), compress_type=ZIP_DEFLATED)
        zf.writestr("meta.xml", _meta_xml(), compress_type=ZIP_DEFLATED)
        zf.writestr("settings.xml", _settings_xml(), compress_type=ZIP_DEFLATED)
        zf.writestr(
            "META-INF/manifest.xml",
            _manifest_xml(spec.mimetype),
            compress_type=ZIP_DEFLATED,
        )

    return spec.mimetype, buffer.getvalue()
