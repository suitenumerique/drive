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

// `acl` must match the ACL signed in the presigned URL (the backend's
// AWS_S3_UPLOAD_ACL), and be omitted when the URL signs none.
export async function putToS3(
  uploadUrl: string,
  body: ArrayBuffer,
  signal?: AbortSignal,
  acl?: string,
): Promise<void> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/octet-stream',
  };
  if (acl) {
    headers['X-amz-acl'] = acl;
  }
  const resp = await fetch(uploadUrl, {
    method: 'PUT',
    body: new Uint8Array(body),
    headers,
    signal,
  });
  if (!resp.ok) {
    throw new Error(`S3 upload failed: ${resp.status}`);
  }
}
