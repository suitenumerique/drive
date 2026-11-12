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
 * The name asked for a staged copy of a file's content: its title, with the
 * extension of its current filename when the title lacks it (a document created
 * from a template is titled without it, and editors such as OnlyOffice read the
 * file's type from the name). The backend sanitizes it and places it in a folder
 * of its own, as for an upload, and answers the filename to use.
 */
export function stagedName(title: string, filename?: string | null): string {
  const extension = extensionOf(filename);
  return extension && !title.toLowerCase().endsWith(extension.toLowerCase())
    ? `${title}${extension}`
    : title;
}
