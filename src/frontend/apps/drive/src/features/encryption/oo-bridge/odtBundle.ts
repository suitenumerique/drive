/**
 * ODT/OOXML archive helpers.
 *
 * We no longer embed a sidecar `.drive/editor.bin` inside the rendered
 * archive. Cross-peer ID alignment is now handled purely peer-to-peer
 * via the `oo:state-response` / `oo:checkpoint-reload` channels in
 * `encryptedRelay.ts` and `OOEditor.tsx`: a joiner fetches live
 * baseBin + chain from an existing peer, so the S3 archive doesn't
 * need to carry any OO-internal state.
 *
 * This module only exposes `extractMedia` now, used on the join path
 * to pull image bytes out of the archive. Media is never duplicated —
 * it lives in `Pictures/` (ODT) or `word|xl|ppt/media/` (OOXML) as
 * usual; the native bin references images by name only.
 */

import { unzipSync } from 'fflate';

/**
 * Extract media files (images, etc.) from the ODT/OOXML archive.
 * Used when we bypass x2t conversion (e.g. loading from a peer-
 * supplied baseBin): x2t normally also produces the media list, so we
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
