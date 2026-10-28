export function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function fromBase64(b64: string): ArrayBuffer {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Build the staged S3 object key so that the browser's default "Save As"
 * name (derived from the URL's last path segment for cross-origin downloads)
 * matches the user-visible title — not a raw uuid.
 *
 * Cut to fit the backend's `Item.filename` (255 characters, folder included),
 * extension kept; `.` and `..` are no names (a storage normalises them away).
 */
const FILENAME_MAX_LENGTH = 255;
// Longer than this, what follows the last dot is part of the name.
const EXTENSION_MAX_LENGTH = 16;

export function stagedFilename(title: string): string {
  const folder = crypto.randomUUID();
  let safe = title.replace(/[/\\\0]/g, "_");
  if (safe === "" || safe === "." || safe === "..") {
    safe = "file";
  }
  // Code points, as the database counts them, and never half a surrogate pair.
  const chars = Array.from(safe);
  const room = FILENAME_MAX_LENGTH - folder.length - 1;
  if (chars.length > room) {
    const dot = safe.lastIndexOf(".");
    const extension =
      dot > 0 && safe.length - dot <= EXTENSION_MAX_LENGTH
        ? Array.from(safe.slice(dot))
        : [];
    safe =
      chars.slice(0, room - extension.length).join("") + extension.join("");
  }
  return `${folder}/${safe}`;
}
