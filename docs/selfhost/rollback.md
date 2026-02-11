# Rollback runbook (v1) — Docker-first, Compose baseline

This runbook targets the **Docker Compose baseline** and assumes you have a
known-good version/tag to return to.

Rollback is only “safe” if your database state is compatible with the target
version. If you already applied non-backward-compatible migrations, rollback
may require a **database restore**.

## Prerequisites

Before rolling back:

1. Identify the **known-good version** (image tags, or Git tag/commit).
2. Determine whether the failed upgrade ran migrations (Step 3 in the upgrade
   runbook).
3. Have a backup from **before** the upgrade attempt (DB + S3 bucket). See
   `docs/installation/backup-restore.md`.

## Rollback procedure (ordering is mandatory)

### 0) Decide whether a DB restore is required

- If the upgrade **did not** run migrations: you can typically rollback by
  pinning the known-good version and restarting services.
- If the upgrade **did** run migrations: you must assume migrations may be
  non-backward-compatible. In that case, rollback may require restoring the DB
  backup taken before the upgrade.

### 1) Quiesce writes

Stop app components that can write:

- `docker compose stop frontend-dev app-dev celery-dev`

### 2) (If required) Restore the database

Follow the DB restore steps in `docs/installation/backup-restore.md` (“Restore
procedure → Restore the PostgreSQL database”).

Do not attempt “down migrations” unless you have an explicit, reviewed plan for
your specific version pair.

### 3) Pin + pull (or build) the known-good version

Choose **one** path:

- **Image-based deployment (recommended):**
  1. Update your Compose file to pin backend/frontend image tags to the
     known-good version.
  2. Pull images: `docker compose pull`
- **Source-built deployment:**
  1. Check out the known-good Git tag/commit.
  2. Build: `docker compose build --pull`

### 4) Restart services

- `docker compose up -d`

If you changed images, prefer:

- `docker compose up -d --force-recreate`

### 5) Post-rollback smoke checks (deterministic)

Run the checklist:

- `docs/selfhost/smoke-checklist.md`

## Object storage compatibility notes

- Preserve the **same bucket name** and **all object keys/prefixes** (e.g.
  `item/<uuid>/...`). Missing prefixes can break previews/WOPI/media.
- If the upgrade wrote new objects, a DB rollback without an S3 rollback can
  still surface mismatches. When in doubt, restore DB + S3 from the same backup
  point.

