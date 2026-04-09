# WOPI + Encryption Integration Points

## Current WOPI Flow (no encryption)

```
Frontend                     Drive Backend (WOPI)              S3                Collabora/OnlyOffice
   |                              |                            |                        |
   |-- GET /items/{id}/wopi/ ---->|                            |                        |
   |<-- {access_token, launch_url}|                            |                        |
   |                              |                            |                        |
   |-- POST launch_url (token) ---|----------------------------|--------------------->>|
   |                              |                            |                        |
   |                              |<--- GET /wopi/files/{id}/ -------------------------|
   |                              |---- CheckFileInfo response ----------------------->|
   |                              |                            |                        |
   |                              |<--- GET /wopi/files/{id}/contents/ -----------------|
   |                              |---- s3.get_object -------->|                        |
   |                              |<--- file content (plain) --|                        |
   |                              |---- StreamingHttpResponse ----------------------->|
   |                              |                            |                        |
   |                              |    ... user edits ...      |                        |
   |                              |                            |                        |
   |                              |<--- POST /wopi/files/{id}/contents/ (PUT) ---------|
   |                              |---- s3.save(file_key) ---->|                        |
   |                              |---- 200 OK --------------------------------------------->|
```

## Encrypted Files — Where to Intercept

There are exactly **2 methods** in `src/backend/wopi/viewsets.py` that touch file content:

### 1. GetFile — `_get_file_content()` (line 117)

```python
# Current code (line 131-136):
s3_client = default_storage.connection.meta.client
file = s3_client.get_object(
    Bucket=default_storage.bucket_name,
    Key=item.file_key,               # <-- reads ENCRYPTED content from S3
)
return StreamingHttpResponse(
    streaming_content=file["Body"].iter_chunks(),  # <-- serves to Collabora AS-IS
    ...
)
```

**Integration point**: After `s3_client.get_object()` and before `StreamingHttpResponse`,
decrypt the content if `item.is_encrypted`:

```python
if item.is_encrypted:
    encrypted_content = file["Body"].read()
    symmetric_key = get_session_symmetric_key(request.auth)  # from cache
    decrypted_content = decrypt_content(encrypted_content, symmetric_key)
    return HttpResponse(
        decrypted_content,
        content_type=item.mimetype,
        headers={...},
    )
```

### 2. PutFile — `_put_file_content()` (line 148)

```python
# Current code (line 174-180):
file = ContentFile(request.body)                  # <-- plain content from Collabora
default_storage.save(item.file_key, file)         # <-- saves to S3 AS-IS (plain)
```

**Integration point**: Before `default_storage.save()`,
encrypt the content if `item.is_encrypted`:

```python
if item.is_encrypted:
    symmetric_key = get_session_symmetric_key(request.auth)
    encrypted_content = encrypt_content(request.body, symmetric_key)
    file = ContentFile(encrypted_content)
default_storage.save(item.file_key, file)
```

## How the Symmetric Key Reaches the Server

The challenge: E2E encryption means the server doesn't have the key.
The key must come from the frontend when the user initiates a WOPI session.

### Proposed flow:

```
Frontend                          Drive Backend                    Cache (Redis)
   |                                   |                              |
   | 1. vault.decryptWithKey(          |                              |
   |    encryptedSymmetricKey,         |                              |
   |    encryptedKeyChain)             |                              |
   |    → raw symmetric key            |                              |
   |                                   |                              |
   | 2. POST /items/{id}/wopi/        |                              |
   |    body: { symmetric_key }        |                              |
   |                                   |-- cache.set(                 |
   |                                   |     key=wopi_enc:{token},    |
   |                                   |     value=symmetric_key,     |
   |                                   |     ttl=WOPI_TOKEN_TIMEOUT)  |
   |                                   |                              |
   |<-- {access_token, launch_url} ----|                              |
   |                                   |                              |
   | ... WOPI session starts ...       |                              |
   |                                   |                              |
   |                              GetFile:                            |
   |                                   |-- cache.get(wopi_enc:{tok}) -|
   |                                   |<-- symmetric_key ------------|
   |                                   |-- decrypt(s3_content, key)   |
   |                                   |-- serve to Collabora         |
   |                              PutFile:                            |
   |                                   |-- cache.get(wopi_enc:{tok}) -|
   |                                   |<-- symmetric_key ------------|
   |                                   |-- encrypt(body, key)         |
   |                                   |-- save to S3 (encrypted)     |
   |                                   |                              |
   | ... session ends / token expires  |                              |
   |                                   |-- cache expires → key gone   |
```

### Key characteristics:
- Symmetric key is **only in Redis memory**, never on disk, never in DB
- Key has the **same TTL as the WOPI access token** — auto-expires
- The key is tied to a specific WOPI session (one key per token)
- When the session expires, the key is gone from Redis

### Trade-off:
- This is NOT pure E2E during the WOPI session — the server temporarily holds the symmetric key in memory
- But the file content is **never stored in plain on S3**
- The key never touches the database
- The key auto-expires with the session

## Collaboration (Multiple Users Editing)

### How Collabora handles collaboration:
- Multiple users open the same file in Collabora
- Collabora server manages the document state internally
- Each user has their own WOPI access token
- GetFile is called once (first user), PutFile when saving

### With encryption:
- Each user provides the symmetric key when opening the WOPI session
- All tokens for the same file share the same symmetric key (it's the file's key)
- GetFile decrypts once, Collabora handles collaboration internally
- PutFile encrypts on save

### Collabora WebSocket:
- Collabora uses WebSocket between browser and Collabora server for real-time sync
- This WebSocket is **inside the Collabora iframe** (cross-origin)
- We cannot intercept it from the Drive frontend
- The data flowing through this WebSocket is Collabora's internal protocol (LOOL/COOL)
- It contains document deltas, cursor positions, etc.

### Options for WebSocket encryption:
1. **Don't encrypt the WebSocket** — Collabora's WebSocket goes over HTTPS (TLS), so transport is encrypted. The concern is the Collabora server sees plaintext deltas. This is the same trust model as the GetFile/PutFile middleware.
2. **Investigate Collabora plugins** — Collabora may support plugins that could intercept content. Needs investigation.
3. **Custom relay** — Like Docs does with HocusPocus, but for Collabora's protocol. Very complex, likely not feasible.

## Implementation Plan

### Phase 1 (current): Disable WOPI for encrypted files
- `wopi: false` in abilities when `is_encrypted`
- Use `EncryptedFileViewer` for preview (client-side decryption)

### Phase 2: WOPI middleware for single-user editing
- Modify `GET /items/{id}/wopi/` to accept symmetric key for encrypted files
- Store key in Redis with WOPI token TTL
- Add decrypt/encrypt middleware in `_get_file_content()` / `_put_file_content()`
- Frontend: resolve key chain in vault, pass key when initiating WOPI session

### Phase 3: Multi-user collaboration investigation
- Test if multiple users can edit with the middleware approach
- Investigate Collabora WebSocket encryption options
- Document trust model and trade-offs
