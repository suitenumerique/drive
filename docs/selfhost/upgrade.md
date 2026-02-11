# Upgrade runbook (v1) — Docker-first, Compose baseline

This runbook targets the **Docker Compose baseline**.

It is written to be **deterministic** and **no-leak**:

- do not paste secrets (credentials, tokens) into terminals, docs, or artifacts,
- prefer `--env-file` over inline env vars (avoid shell history leaks),
- do not log or export signed URLs or SigV4 headers.

## Prerequisites

Before upgrading:

1. Read the target version’s release notes (and any breaking changes).
2. Take a fresh backup (DB + S3 bucket). See `docs/installation/backup-restore.md`.
3. Decide your rollback point (a known-good version/tag) and keep it recorded.

## Upgrade procedure (ordering is mandatory)

### 0) Record the current version (deterministic)

Record the exact version you are running (one of):

- image tags (recommended for operators), or
- Git tag / commit SHA (if you build images from source).

### 1) Pin + pull (or build) the target images

Choose **one** path and keep it explicit:

- **Image-based deployment (recommended):**
  1. Update your Compose file to pin backend/frontend image tags to the target
     version (avoid `:latest`).
  2. Pull images: `docker compose pull`
- **Source-built deployment (development/advanced):**
  1. Check out the target Git tag/commit.
  2. Build with fresh bases: `docker compose build --pull`

### 2) Quiesce writes (recommended)

Stop components that can write while you run migrations:

- `docker compose stop frontend-dev app-dev celery-dev`

If your deployment has different service names, stop the equivalents
(web/app + workers).

### 3) Run database migrations (deterministic)

Run migrations exactly once:

- `docker compose run --rm app-dev python manage.py migrate --noinput`

Notes:

- If migrations fail, **do not retry blindly**. Capture the deterministic error
  and decide whether to fix-forward or rollback (see `docs/selfhost/rollback.md`).
- Some migrations are not backward-compatible; this is why the backup is
  mandatory.

### 4) Restart services on the new version

Start the stack:

- `docker compose up -d`

If you pulled/built new images, you may prefer a recreate:

- `docker compose up -d --force-recreate`

### 5) Post-upgrade smoke checks (deterministic)

Run the checklist:

- `docs/selfhost/smoke-checklist.md`

