/**
 * Load an empty ODT / ODS / ODP template at runtime for the "New document"
 * flow inside an encrypted folder.
 *
 * The templates are static assets served from `/templates/`, fetched from
 * The Document Foundation's `odftoolkit` reference library. See
 * `public/templates/README.md` for provenance and the rationale (short
 * version: the server can't produce plaintext inside encrypted subtrees,
 * 0-byte files crash OnlyOffice on ODS, and hand-rolled ODF is fragile).
 */

export type BlankOdfExtension = 'odt' | 'ods' | 'odp';

const TEMPLATE_PATH_BY_EXT: Record<BlankOdfExtension, string> = {
  odt: '/templates/OdfTextDocument.odt',
  ods: '/templates/OdfSpreadsheetDocument.ods',
  odp: '/templates/OdfPresentationDocument.odp',
};

export async function createBlankOdf(
  extension: BlankOdfExtension,
): Promise<ArrayBuffer> {
  const url = TEMPLATE_PATH_BY_EXT[extension];
  const response = await fetch(url, { cache: 'force-cache' });
  if (!response.ok) {
    throw new Error(
      `Failed to load blank ODF template ${url} (${response.status})`,
    );
  }
  return response.arrayBuffer();
}
