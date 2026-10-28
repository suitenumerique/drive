# Blank ODF templates

Empty, valid ODT / ODS / ODP documents used when the user clicks
"New text document" / "New spreadsheet" / "New presentation" **inside an
encrypted folder**.

## Why these files are here

In encrypted folders the backend has no access to the document keys, so it
cannot generate or serve a plaintext template on the user's behalf (the way
it does for non-encrypted folders via `/children/` with `extension=`).
The encrypted create flow therefore needs seed bytes the client can
encrypt before upload.

We don't want to:

- spin up the OnlyOffice editor just to export an empty file (heavy, slow,
  race-y)
- ship a 0-byte file — OnlyOffice's spreadsheet reader crashes on empty
  input (`ReadDefCellStyles` → `Cannot read properties of null`); ODT/ODP
  happen to survive but behaviour is clearly undefined
- hand-roll the ODF ZIPs ourselves — spec-compliant is doable but fragile
  and hard to audit

So we pulled the reference blank documents from **The Document Foundation's
own `odftoolkit`**, the Java library that is the de-facto reference
implementation of ISO/IEC 26300 (ODF). They have been stable since 2011
and are bundled unchanged in every release of that library. There is no
reason to touch or regenerate them.

## Source

Fetched once, verbatim, from:

| File                          | Size    | URL                                                                                                             |
| ----------------------------- | ------- | --------------------------------------------------------------------------------------------------------------- |
| `OdfTextDocument.odt`         | 9,897 B | <https://raw.githubusercontent.com/tdf/odftoolkit/master/odfdom/src/main/resources/OdfTextDocument.odt>         |
| `OdfSpreadsheetDocument.ods`  | 5,491 B | <https://raw.githubusercontent.com/tdf/odftoolkit/master/odfdom/src/main/resources/OdfSpreadsheetDocument.ods>  |
| `OdfPresentationDocument.odp` | 7,715 B | <https://raw.githubusercontent.com/tdf/odftoolkit/master/odfdom/src/main/resources/OdfPresentationDocument.odp> |

Upstream repo: <https://github.com/tdf/odftoolkit>
Upstream license: Apache License 2.0.

## How they're used

The client fetches `/templates/<file>` at create time, wraps the bytes in
a `File`, encrypts them with the parent folder's key chain, and uploads
via the same path as drag-drop. OnlyOffice then opens the encrypted
document normally through the x2t pipeline.
