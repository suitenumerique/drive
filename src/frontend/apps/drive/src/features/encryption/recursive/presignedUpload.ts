import { fetchAPI } from "@/features/api/fetchApi";

/**
 * A file's stored content, with the ETag it was served under: the commit sends
 * it back, and the server refuses a file whose content changed since. Never from
 * the browser's cache, whose copy may predate the latest save.
 */
export async function downloadForStaging(
  url: string,
  signal?: AbortSignal,
): Promise<{ body: ArrayBuffer; etag: string | null }> {
  const resp = await fetch(url, {
    credentials: "include",
    cache: "no-store",
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Download failed: ${resp.status}`);
  }
  return { body: await resp.arrayBuffer(), etag: resp.headers.get("ETag") };
}

// The URL signs `size`: the body uploaded to it must be exactly that long. The
// backend places the copy and answers its filename, the one to point the item at.
export async function getEncryptionUploadUrl(
  itemId: string,
  name: string,
  size: number,
  signal?: AbortSignal,
): Promise<{ uploadUrl: string; filename: string }> {
  const resp = await fetchAPI(`items/${itemId}/encryption-upload-url/`, {
    method: "POST",
    body: JSON.stringify({ filename: name, size }),
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Failed to get upload URL: ${resp.status}`);
  }
  const { upload_url, filename } = await resp.json();
  return { uploadUrl: upload_url, filename };
}

// `acl` must match the ACL signed in the presigned URL (the backend's
// AWS_S3_UPLOAD_ACL), and be omitted when the URL signs none.
export async function putToS3(
  uploadUrl: string,
  body: ArrayBuffer,
  signal?: AbortSignal,
  acl?: string,
): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/octet-stream",
  };
  if (acl) {
    headers["X-amz-acl"] = acl;
  }
  const resp = await fetch(uploadUrl, {
    method: "PUT",
    body: new Uint8Array(body),
    headers,
    signal,
  });
  if (!resp.ok) {
    throw new Error(`S3 upload failed: ${resp.status}`);
  }
}
