import { fetchAPI } from '@/features/api/fetchApi';

export async function getEncryptionUploadUrl(
  itemId: string,
  filename: string,
  signal?: AbortSignal,
): Promise<string> {
  const resp = await fetchAPI(`items/${itemId}/encryption-upload-url/`, {
    method: 'POST',
    body: JSON.stringify({ filename }),
    signal,
  });
  if (!resp.ok) {
    throw new Error(`Failed to get upload URL: ${resp.status}`);
  }
  const { upload_url } = await resp.json();
  return upload_url;
}

export async function putToS3(
  uploadUrl: string,
  body: ArrayBuffer,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(uploadUrl, {
    method: 'PUT',
    body: new Uint8Array(body),
    headers: {
      'X-amz-acl': 'private',
      'Content-Type': 'application/octet-stream',
    },
    signal,
  });
  if (!resp.ok) {
    throw new Error(`S3 upload failed: ${resp.status}`);
  }
}
