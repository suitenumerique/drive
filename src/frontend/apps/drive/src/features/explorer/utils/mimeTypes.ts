import { Item, ItemUploadState } from "@/features/drivers/types";
import { getMimeCategory, MimeCategory } from "@gouvfr-lasuite/ui-components";
import { getExtension } from "../utils/utils";

/** Extension → MIME mapping used when the stored mimetype is unreliable
 *  (encrypted items always report application/octet-stream on the server
 *  because the backend can't inspect ciphertext). Keep it tight: only the
 *  categories the UI actually routes on (viewers, icons, format labels).
 */
const EXTENSION_TO_MIME: Record<string, string> = {
  // Docs — prefer text/plain over text/markdown / application/rtf for
  // formats that OnlyOffice can open as a "word" doc, so the encrypted
  // viewer routes them through OOEditor rather than falling through to
  // "not supported".
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  odt: "application/vnd.oasis.opendocument.text",
  txt: "text/plain",
  rtf: "text/plain",
  md: "text/plain",
  // Spreadsheets
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ods: "application/vnd.oasis.opendocument.spreadsheet",
  csv: "text/csv",
  // Presentations
  ppt: "application/vnd.ms-powerpoint",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  odp: "application/vnd.oasis.opendocument.presentation",
  // PDF
  pdf: "application/pdf",
  // Images
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  gif: "image/gif",
  webp: "image/webp",
  bmp: "image/bmp",
  svg: "image/svg+xml",
  tiff: "image/tiff",
  tif: "image/tiff",
  // Audio
  mp3: "audio/mpeg",
  wav: "audio/wav",
  ogg: "audio/ogg",
  flac: "audio/flac",
  aac: "audio/aac",
  m4a: "audio/mp4",
  // Video
  mp4: "video/mp4",
  webm: "video/webm",
  mov: "video/quicktime",
  avi: "video/x-msvideo",
  mkv: "video/x-matroska",
  // Archive
  zip: "application/zip",
  "7z": "application/x-7z-compressed",
  rar: "application/x-rar-compressed",
  tar: "application/x-tar",
};

/**
 * Derive the effective mimetype, substituting an extension-based guess
 * when the backend-stored one is meaningless. Triggers when an item is
 * encrypted AND the server stored application/octet-stream because it
 * couldn't inspect the ciphertext (direct-upload-into-encrypted-folder
 * case — recursively encrypted items keep their original mimetype).
 * The client knows the real type from the filename's extension.
 *
 * Deliberately NOT extended to non-encrypted uploads: for those, the
 * server's magic-byte detection is authoritative. Trusting the filename
 * extension over content-based detection could let a user mislabel a
 * file's type (security-relevant for any path that routes on mimetype).
 */
export const getEffectiveMimetype = (item: Item): string | undefined => {
  const stored = item.mimetype ?? undefined;
  if (item.is_encrypted && stored === "application/octet-stream") {
    const extension = getExtension(item);
    const byExtension = extension && EXTENSION_TO_MIME[extension.toLowerCase()];
    if (byExtension) return byExtension;
  }
  return stored;
};

/**
 * Wrapper around the ui-kit getMimeCategory function to add support for
 * suspicious items.
 */
export const getItemMimeCategory = (item: Item): MimeCategory => {
  const uploadState = item.upload_state;
  if (uploadState === ItemUploadState.SUSPICIOUS) {
    return MimeCategory.SUSPICIOUS;
  }

  const mimetype = getEffectiveMimetype(item);
  const extension = getExtension(item);
  if (!mimetype) {
    return MimeCategory.OTHER;
  }

  return getMimeCategory(mimetype, extension);
};

export const getFormatTranslationKey = (item: Item) => {
  const category = getItemMimeCategory(item);
  return `mime.${category}`;
};
