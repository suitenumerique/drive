// FilePreview asks pdf.js for the JPEG 2000 / JBIG2 decoders, the standard
// fonts and the CJK cmaps at the site root. pdf.js does not fail when those
// 404: it logs a warning and skips the resource, so a scanned PDF silently
// renders blank or half-drawn. Copying them out of the pdfjs-dist that
// react-pdf resolves keeps them on the same version as the worker.
import { cpSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const pdfjs = dirname(require.resolve("pdfjs-dist/package.json"));
const publicDir = join(import.meta.dirname, "..", "public");

for (const folder of ["cmaps", "standard_fonts", "wasm"]) {
  cpSync(join(pdfjs, folder), join(publicDir, folder), { recursive: true });
}
