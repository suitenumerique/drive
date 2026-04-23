/**
 * ODT/OOXML bundle helpers for the `.drive/editor.bin` sidecar.
 *
 * Why this exists
 * ---------------
 * OnlyOffice regenerates its internal object ids (Run handles, Paragraph
 * ids, etc.) every time a document is loaded from ODT/OOXML: a pure
 * counter starts at 0 and increments for each element parsed. That means
 * two peers loading the same bytes at the same time DO get matching ids
 * — great — but a peer that reloads mid-session gets a fresh id space
 * that no longer matches peers still running their original session.
 * The live peer keeps broadcasting `saveChanges` that reference the old
 * ids, the reloaded peer can't resolve them, and OT patches either
 * silently drop or crash on `undefined`.
 *
 * The fix mirrors what CryptPad does with their `.bin` checkpoints:
 * persist OO's native binary state (`asc_nativeGetFile()`) alongside
 * the rendered ODT. On reload, feed the native state back into OO so
 * every object comes back with its exact previous id.
 *
 * To keep the ODT interoperable with LibreOffice/Word/etc. we write
 * the native blob as an EXTRA entry inside the ODT's own ZIP archive,
 * under `.drive/editor.bin`. External tools ignore unknown entries; on
 * round-trip through them the sidecar is dropped (acceptable: next
 * Drive open just falls back to fresh-id load).
 *
 * Media are NOT duplicated. `asc_nativeGetFile()` emits a pure-structure
 * blob — it references images by name (`image1.png` etc.) but never
 * embeds the bytes. The real media stay in the ODT's `Pictures/`
 * folder as usual and are resolved at load via
 * `AscCommon.g_oDocumentUrls.addImageUrl()`.
 */

import { unzipSync, zipSync, strToU8, strFromU8 } from 'fflate';

/** Path of the sidecar entry inside the ODT ZIP. */
const SIDECAR_PATH = '.drive/editor.bin';

/**
 * Inject OO's native binary state (`asc_nativeGetFile()` return value)
 * as a sidecar entry in an existing ODT/DOCX/XLSX/PPTX archive.
 *
 * The native string has the shape `"DOCY;v5;{size};{base64data}"` and
 * is written verbatim — x2t isn't involved.
 *
 * Returns a fresh archive with the sidecar entry present. Any prior
 * sidecar is overwritten.
 */
export function injectDriveBin(
  archiveBytes: Uint8Array,
  binString: string,
): Uint8Array {
  const files = unzipSync(archiveBytes);
  files[SIDECAR_PATH] = strToU8(binString);
  return zipSync(files);
}

/**
 * Extract the sidecar native binary string from an ODT archive, if
 * present. Returns null when the archive has no sidecar (freshly
 * created file, round-tripped through an external editor, etc.) — the
 * caller should then fall back to the normal ODT → x2t → .bin path.
 */
export function extractDriveBin(archiveBytes: Uint8Array): string | null {
  try {
    const files = unzipSync(archiveBytes, {
      filter: f => f.name === SIDECAR_PATH,
    });
    const entry = files[SIDECAR_PATH];
    if (!entry) return null;
    return strFromU8(entry);
  } catch {
    // Not a valid ZIP, or unzip refused — treat as "no sidecar", let
    // the x2t fallback diagnose the real problem.
    return null;
  }
}

/**
 * Extract media files (images, etc.) from the ODT/OOXML archive.
 * Used when we bypass x2t conversion and load OO directly from the
 * sidecar `.bin`: x2t normally also produces the media list, so we
 * must reproduce it from the archive ourselves.
 *
 * Scope is limited to `Pictures/` (ODT), `word/media/`, `xl/media/`,
 * `ppt/media/` (OOXML). Entries are returned keyed by the plain
 * filename — that's how OO's `g_oDocumentUrls.addImageUrl(name, url)`
 * expects them.
 */
export function extractMedia(
  archiveBytes: Uint8Array,
): Array<{ name: string; data: Uint8Array }> {
  try {
    const files = unzipSync(archiveBytes, {
      filter: f => {
        const n = f.name;
        return (
          n.startsWith('Pictures/') ||
          n.startsWith('word/media/') ||
          n.startsWith('xl/media/') ||
          n.startsWith('ppt/media/')
        );
      },
    });
    const out: Array<{ name: string; data: Uint8Array }> = [];
    for (const [path, data] of Object.entries(files)) {
      const slash = path.lastIndexOf('/');
      const name = slash >= 0 ? path.slice(slash + 1) : path;
      if (!name) continue;
      out.push({ name, data });
    }
    return out;
  } catch {
    return [];
  }
}
