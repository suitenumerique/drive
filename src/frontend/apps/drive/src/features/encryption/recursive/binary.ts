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

const FILENAME_MAX_LENGTH = 255;
// Longer than this, what follows the last dot is part of the name.
const EXTENSION_MAX_LENGTH = 16;

/** The extension of a stored filename (`.odt`), or "" when it has none. */
function extensionOf(filename: string | null | undefined): string {
  const name = filename?.split("/").pop() ?? "";
  const dot = name.lastIndexOf(".");
  return dot > 0 && name.length - dot <= EXTENSION_MAX_LENGTH
    ? name.slice(dot)
    : "";
}

/**
 * Build the staged S3 object key so that the browser's default "Save As"
 * name (derived from the URL's last path segment for cross-origin downloads)
 * matches the user-visible title — not a raw uuid.
 *
 * `filename` is the item's current one: a title can lack the extension (a
 * document created from a template is titled without it), and editors such as
 * OnlyOffice read the file's type from the name, so it is carried over.
 *
 * Cut to fit the backend's `Item.filename` (255 characters, folder included),
 * extension kept; `.` and `..` are no names (a storage normalises them away).
 */
export function stagedFilename(
  title: string,
  filename?: string | null,
): string {
  const folder = crypto.randomUUID();
  const extension = extensionOf(filename);
  const named =
    extension && !title.toLowerCase().endsWith(extension.toLowerCase())
      ? `${title}${extension}`
      : title;
  let safe = named.replace(/[/\\\0]/g, "_");
  if (safe === "" || safe === "." || safe === "..") {
    safe = "file";
  }
  // Code points, as the database counts them, and never half a surrogate pair.
  const chars = Array.from(safe);
  const room = FILENAME_MAX_LENGTH - folder.length - 1;
  if (chars.length > room) {
    const dot = safe.lastIndexOf(".");
    const kept =
      dot > 0 && safe.length - dot <= EXTENSION_MAX_LENGTH
        ? Array.from(safe.slice(dot))
        : [];
    safe = chars.slice(0, room - kept.length).join("") + kept.join("");
  }
  return `${folder}/${safe}`;
}
