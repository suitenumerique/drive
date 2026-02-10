# Run Report — Story 2.4 (Backup / restore runbook)

- Run ID: `20260210-212117-2.4`
- Date (UTC): 2026-02-10
- Branch: `story/2.4-backup-restore-runbook`
- PR: #17 (draft)

## Goal

Provide a Docker-first backup/restore runbook (DB + object storage + optional
fixtures) with a deterministic post-restore smoke checklist, without leaking
secrets.

## What changed

- Added `docs/installation/backup-restore.md`:
  - concrete DB dump/restore steps (PostgreSQL)
  - object storage mirror guidance (S3 bucket, prefix/layout preservation)
  - explicit versioning note for WOPI deployments
  - deterministic post-restore smoke checklist (login/browse/preview/upload/media/share)
- Linked the runbook from `docs/installation/README.md`.

## Verification (dev-owned)

Documentation verification is manual:

- Ensure commands are copy/pastable and do not leak secrets.
- Follow the runbook end-to-end on a local Docker Compose deployment.

Record any adjustments needed in follow-up commits and update `gates.md`.

