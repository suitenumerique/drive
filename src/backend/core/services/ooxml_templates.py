"""Minimal OOXML (Office Open XML) templates for new documents.

ONLYOFFICE DocumentServer (in our dev/LAN setup) does not advertise the WOPI
`editnew` action for `.docx/.xlsx/.pptx` in discovery, so a 0-byte placeholder
cannot be initialized via a lock-less PutFile on create.

To keep "create + open" functional, we generate minimal valid OOXML packages
in code (ZIP containers) without shipping binary assets.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(frozen=True, slots=True)
class OoxmlTemplateSpec:
    extension: str
    mimetype: str
    files: dict[str, str]


_DOCPROPS_CORE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
    "  <dc:title/>\n"
    "  <dc:subject/>\n"
    "  <dc:creator>Drive</dc:creator>\n"
    "  <cp:keywords/>\n"
    "  <dc:description/>\n"
    "  <cp:lastModifiedBy>Drive</cp:lastModifiedBy>\n"
    '  <dcterms:created xsi:type="dcterms:W3CDTF">2000-01-01T00:00:00Z</dcterms:created>\n'
    '  <dcterms:modified xsi:type="dcterms:W3CDTF">2000-01-01T00:00:00Z</dcterms:modified>\n'
    "</cp:coreProperties>\n"
)

_DOCPROPS_APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">\n'
    "  <Application>Drive</Application>\n"
    "</Properties>\n"
)


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


_OOXML_TEMPLATES: dict[str, OoxmlTemplateSpec] = {
    "docx": OoxmlTemplateSpec(
        extension="docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        files={
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                '  <Default Extension="xml" ContentType="application/xml"/>\n'
                '  <Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
                '  <Override PartName="/word/styles.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>\n'
                '  <Override PartName="/docProps/core.xml" '
                'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
                '  <Override PartName="/docProps/app.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
                "</Types>\n"
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>\n'
                '  <Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
                'Target="docProps/core.xml"/>\n'
                '  <Relationship Id="rId3" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
                'Target="docProps/app.xml"/>\n'
                "</Relationships>\n"
            ),
            "word/document.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
                "  <w:body>\n"
                "    <w:p/>\n"
                "    <w:sectPr>\n"
                '      <w:pgSz w:w="11906" w:h="16838"/>\n'
                '      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
                'w:header="720" w:footer="720" w:gutter="0"/>\n'
                "    </w:sectPr>\n"
                "  </w:body>\n"
                "</w:document>\n"
            ),
            "word/_rels/document.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                'Target="styles.xml"/>\n'
                "</Relationships>\n"
            ),
            "word/styles.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
                '  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">\n'
                '    <w:name w:val="Normal"/>\n'
                "    <w:qFormat/>\n"
                "  </w:style>\n"
                "</w:styles>\n"
            ),
            "docProps/core.xml": _DOCPROPS_CORE_XML,
            "docProps/app.xml": _DOCPROPS_APP_XML,
        },
    ),
    "xlsx": OoxmlTemplateSpec(
        extension="xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        files={
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                '  <Default Extension="xml" ContentType="application/xml"/>\n'
                '  <Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
                '  <Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
                '  <Override PartName="/xl/styles.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>\n'
                '  <Override PartName="/docProps/core.xml" '
                'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
                '  <Override PartName="/docProps/app.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
                "</Types>\n"
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>\n'
                '  <Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
                'Target="docProps/core.xml"/>\n'
                '  <Relationship Id="rId3" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
                'Target="docProps/app.xml"/>\n'
                "</Relationships>\n"
            ),
            "xl/workbook.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
                "  <sheets>\n"
                '    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>\n'
                "  </sheets>\n"
                "</workbook>\n"
            ),
            "xl/_rels/workbook.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/>\n'
                '  <Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                'Target="styles.xml"/>\n'
                "</Relationships>\n"
            ),
            "xl/worksheets/sheet1.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
                "  <sheetData/>\n"
                "</worksheet>\n"
            ),
            "xl/styles.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
                '  <fonts count="1">\n'
                "    <font>\n"
                '      <sz val="11"/>\n'
                '      <color theme="1"/>\n'
                '      <name val="Calibri"/>\n'
                '      <family val="2"/>\n'
                "    </font>\n"
                "  </fonts>\n"
                '  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>\n'
                '  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\n'
                '  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>\n'
                '  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>\n'
                '  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>\n'
                "</styleSheet>\n"
            ),
            "docProps/core.xml": _DOCPROPS_CORE_XML,
            "docProps/app.xml": _DOCPROPS_APP_XML,
        },
    ),
    "pptx": OoxmlTemplateSpec(
        extension="pptx",
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        files={
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                '  <Default Extension="xml" ContentType="application/xml"/>\n'
                '  <Override PartName="/ppt/presentation.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>\n'
                '  <Override PartName="/ppt/slides/slide1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>\n'
                '  <Override PartName="/ppt/slideMasters/slideMaster1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>\n'
                '  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>\n'
                '  <Override PartName="/ppt/theme/theme1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>\n'
                '  <Override PartName="/docProps/core.xml" '
                'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\n'
                '  <Override PartName="/docProps/app.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\n'
                "</Types>\n"
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="ppt/presentation.xml"/>\n'
                '  <Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
                'Target="docProps/core.xml"/>\n'
                '  <Relationship Id="rId3" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
                'Target="docProps/app.xml"/>\n'
                "</Relationships>\n"
            ),
            "ppt/presentation.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">\n'
                "  <p:sldMasterIdLst>\n"
                '    <p:sldMasterId id="2147483648" r:id="rId1"/>\n'
                "  </p:sldMasterIdLst>\n"
                "  <p:sldIdLst>\n"
                '    <p:sldId id="256" r:id="rId2"/>\n'
                "  </p:sldIdLst>\n"
                '  <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>\n'
                '  <p:notesSz cx="6858000" cy="9144000"/>\n'
                "</p:presentation>\n"
            ),
            "ppt/_rels/presentation.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
                'Target="slideMasters/slideMaster1.xml"/>\n'
                '  <Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                'Target="slides/slide1.xml"/>\n'
                "</Relationships>\n"
            ),
            "ppt/slideMasters/slideMaster1.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">\n'
                "  <p:cSld>\n"
                "    <p:spTree>\n"
                "      <p:nvGrpSpPr>\n"
                '        <p:cNvPr id="1" name=""/>\n'
                "        <p:cNvGrpSpPr/>\n"
                "        <p:nvPr/>\n"
                "      </p:nvGrpSpPr>\n"
                "      <p:grpSpPr>\n"
                "        <a:xfrm>\n"
                '          <a:off x="0" y="0"/>\n'
                '          <a:ext cx="0" cy="0"/>\n'
                '          <a:chOff x="0" y="0"/>\n'
                '          <a:chExt cx="0" cy="0"/>\n'
                "        </a:xfrm>\n"
                "      </p:grpSpPr>\n"
                "    </p:spTree>\n"
                "  </p:cSld>\n"
                "  <p:sldLayoutIdLst>\n"
                '    <p:sldLayoutId id="1" r:id="rId1"/>\n'
                "  </p:sldLayoutIdLst>\n"
                "  <p:txStyles/>\n"
                "</p:sldMaster>\n"
            ),
            "ppt/slideMasters/_rels/slideMaster1.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
                'Target="../slideLayouts/slideLayout1.xml"/>\n'
                '  <Relationship Id="rId2" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
                'Target="../theme/theme1.xml"/>\n'
                "</Relationships>\n"
            ),
            "ppt/slideLayouts/slideLayout1.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'type="title" preserve="1">\n'
                "  <p:cSld>\n"
                "    <p:spTree>\n"
                "      <p:nvGrpSpPr>\n"
                '        <p:cNvPr id="1" name=""/>\n'
                "        <p:cNvGrpSpPr/>\n"
                "        <p:nvPr/>\n"
                "      </p:nvGrpSpPr>\n"
                "      <p:grpSpPr>\n"
                "        <a:xfrm>\n"
                '          <a:off x="0" y="0"/>\n'
                '          <a:ext cx="0" cy="0"/>\n'
                '          <a:chOff x="0" y="0"/>\n'
                '          <a:chExt cx="0" cy="0"/>\n'
                "        </a:xfrm>\n"
                "      </p:grpSpPr>\n"
                "    </p:spTree>\n"
                "  </p:cSld>\n"
                "  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>\n"
                "</p:sldLayout>\n"
            ),
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
                'Target="../slideMasters/slideMaster1.xml"/>\n'
                "</Relationships>\n"
            ),
            "ppt/slides/slide1.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">\n'
                "  <p:cSld>\n"
                "    <p:spTree>\n"
                "      <p:nvGrpSpPr>\n"
                '        <p:cNvPr id="1" name=""/>\n'
                "        <p:cNvGrpSpPr/>\n"
                "        <p:nvPr/>\n"
                "      </p:nvGrpSpPr>\n"
                "      <p:grpSpPr>\n"
                "        <a:xfrm>\n"
                '          <a:off x="0" y="0"/>\n'
                '          <a:ext cx="0" cy="0"/>\n'
                '          <a:chOff x="0" y="0"/>\n'
                '          <a:chExt cx="0" cy="0"/>\n'
                "        </a:xfrm>\n"
                "      </p:grpSpPr>\n"
                "    </p:spTree>\n"
                "  </p:cSld>\n"
                "  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>\n"
                "</p:sld>\n"
            ),
            "ppt/slides/_rels/slide1.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                '  <Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
                'Target="../slideLayouts/slideLayout1.xml"/>\n'
                "</Relationships>\n"
            ),
            "ppt/theme/theme1.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'name="Office Theme">\n'
                "  <a:themeElements>\n"
                '    <a:clrScheme name="Office">\n'
                '      <a:dk1><a:srgbClr val="000000"/></a:dk1>\n'
                '      <a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>\n'
                '      <a:dk2><a:srgbClr val="1F497D"/></a:dk2>\n'
                '      <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>\n'
                '      <a:accent1><a:srgbClr val="4F81BD"/></a:accent1>\n'
                '      <a:accent2><a:srgbClr val="C0504D"/></a:accent2>\n'
                '      <a:accent3><a:srgbClr val="9BBB59"/></a:accent3>\n'
                '      <a:accent4><a:srgbClr val="8064A2"/></a:accent4>\n'
                '      <a:accent5><a:srgbClr val="4BACC6"/></a:accent5>\n'
                '      <a:accent6><a:srgbClr val="F79646"/></a:accent6>\n'
                '      <a:hlink><a:srgbClr val="0000FF"/></a:hlink>\n'
                '      <a:folHlink><a:srgbClr val="800080"/></a:folHlink>\n'
                "    </a:clrScheme>\n"
                '    <a:fontScheme name="Office">\n'
                '      <a:majorFont><a:latin typeface="Calibri"/></a:majorFont>\n'
                '      <a:minorFont><a:latin typeface="Calibri"/></a:minorFont>\n'
                "    </a:fontScheme>\n"
                '    <a:fmtScheme name="Office">\n'
                "      <a:fillStyleLst/>\n"
                "      <a:lnStyleLst/>\n"
                "      <a:effectStyleLst/>\n"
                "      <a:bgFillStyleLst/>\n"
                "    </a:fmtScheme>\n"
                "  </a:themeElements>\n"
                "</a:theme>\n"
            ),
            "docProps/core.xml": _DOCPROPS_CORE_XML,
            "docProps/app.xml": _DOCPROPS_APP_XML,
        },
    ),
}


def build_minimal_ooxml_template_bytes(extension: str) -> tuple[str, bytes]:
    """
    Build a minimal, valid OOXML template for the requested extension.

    Returns (mimetype, bytes).
    """
    ext = str(extension or "").strip().lower().lstrip(".")
    spec = _OOXML_TEMPLATES.get(ext)
    if spec is None:
        raise ValueError("unsupported_extension")
    return spec.mimetype, _zip_bytes(spec.files)
