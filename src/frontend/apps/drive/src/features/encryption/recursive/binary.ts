export function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
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
 */
export function stagedFilename(title: string): string {
  const safe = title.replace(/[/\\]/g, '_') || 'file';
  return `${crypto.randomUUID()}/${safe}`;
}
