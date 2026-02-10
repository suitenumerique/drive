# Docker-first backup / restore runbook

This runbook targets the **Docker Compose baseline** (DB + S3-compatible object
storage + optional dev fixtures).

It is written to be **deterministic** and **no-leak**:

- do not paste secrets (credentials, tokens) into terminals, docs, or artifacts,
- prefer `--env-file` over inline env vars (avoid shell history leaks),
- do not log or export signed URLs or SigV4 headers.

## What you must back up (in scope)

1. **Database (PostgreSQL)**: Drive metadata (items, permissions, shares, etc.).
2. **Object storage (S3 bucket)**: file blobs under the Drive bucket, preserving
   **all keys/prefixes** (e.g. `item/<uuid>/...`).
3. **Optional dev/test fixtures**: only if you rely on them (e.g. Keycloak).

## What you do not need to back up (out of scope)

- Redis / caches
- Mailcatcher
- ephemeral worker state

## Backup procedure

### 0) Quiesce writes (recommended)

For a consistent backup, stop Drive app components that can write:

- `docker compose stop frontend-dev app-dev celery-dev`

If you cannot stop traffic (production), use your DB/S3 provider’s snapshotting
tools instead (provider-specific).

### 1) Backup the PostgreSQL database

Create a local folder for artifacts:

- `mkdir -p backups/`

Dump the DB inside the Postgres container to avoid secrets on the command line:

- `docker compose exec -T postgresql sh -lc 'pg_dump -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" --format=custom --file=/tmp/drive-db.dump'`
- `docker compose cp postgresql:/tmp/drive-db.dump backups/drive-db.dump`

Optional integrity check:

- `docker compose exec -T postgresql sh -lc 'pg_restore --list /tmp/drive-db.dump >/dev/null'`

### 2) Backup object storage (S3 bucket)

The restore must preserve the **same bucket name** and **all object keys**.
If you exclude prefixes, previews/WOPI/media may break silently.

Recommended (portable): mirror the bucket via the S3 API using `mc`:

1. Create a file `backups/s3.env` containing your S3 credentials and endpoint
   (restricted permissions, never commit it).
2. Mirror the bucket to disk:
   - `docker run --rm --env-file backups/s3.env -v \"$PWD/backups:/backup\" minio/mc sh -lc 'mc alias set drive \"$AWS_S3_ENDPOINT_URL\" \"$AWS_ACCESS_KEY_ID\" \"$AWS_SECRET_ACCESS_KEY\" && mc mirror --overwrite drive/drive-media-storage /backup/drive-media-storage'`

Notes:

- If **bucket versioning** is required for your deployment (WOPI), ensure the
  destination bucket has versioning enabled *before* restoring objects.
- Mirroring copies the latest state; preserving full version history is
  provider-specific and may require snapshots/replication.

### 3) Optional: Keycloak dev fixture

The development compose file does not persist Keycloak’s DB by default (no
volume is configured for `kc_postgresql`). If you added persistence, back up its
Postgres data similarly to the main DB, and keep your realm/config files (e.g.
`docker/auth/realm.json`) under version control.

## Restore procedure

### 0) Safety

- Restore into a **clean** environment when possible (empty DB + empty bucket).
- Keep the DB restore and bucket restore **paired** (same backup point in time).

### 1) Restore the PostgreSQL database

Copy the dump into the container:

- `docker compose cp backups/drive-db.dump postgresql:/tmp/drive-db.dump`

Restore (drops/recreates objects in-place):

- `docker compose exec -T postgresql sh -lc 'pg_restore --clean --if-exists -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" /tmp/drive-db.dump'`

### 2) Restore object storage (S3 bucket)

Prerequisites (must be true before restoring objects):

- the bucket exists (e.g. `drive-media-storage`)
- **bucket versioning is enabled** if your deployment requires WOPI

Mirror back from disk:

- `docker run --rm --env-file backups/s3.env -v \"$PWD/backups:/backup\" minio/mc sh -lc 'mc alias set drive \"$AWS_S3_ENDPOINT_URL\" \"$AWS_ACCESS_KEY_ID\" \"$AWS_SECRET_ACCESS_KEY\" && mc mirror --overwrite /backup/drive-media-storage drive/drive-media-storage'`

### 3) Start services

- `docker compose up -d`

## Post-restore smoke checklist (deterministic)

Perform these checks in order; each check must have a clear PASS/FAIL outcome.

1. **Login**
   - Action: log in via your configured OIDC IdP.
   - PASS: you land in Drive with the Explorer visible (no infinite loading).
2. **Browse**
   - Action: open a known workspace/folder.
   - PASS: file list renders; navigation works.
3. **Preview**
   - Action: open preview for a known previewable file.
   - PASS: preview renders, or shows a clear actionable error (no hang).
4. **Upload**
   - Action: upload a small test file.
   - PASS: upload completes and the file appears in the expected folder.
5. **`/media` flow**
   - Action: download/open an existing file that uses the `/media` path.
   - PASS: the file loads; failures are actionable and do not leak secrets.
6. **Public share link (if enabled)**
   - Action: open an existing share link in a private window.
   - PASS: share opens, or shows a clear actionable state (no hang).

