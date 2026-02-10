# Story 2.4: Docker-first backup/restore runbook + deterministic post-restore smoke checklist

Status: done

## Story

As an operator,
I want a documented, Docker-first backup/restore procedure (DB + object storage + optional local dev/test IdP fixtures) with a deterministic post-restore smoke checklist,
So that I can recover from incidents and validate service health without ambiguity or leaks.

## Acceptance Criteria

**Given** I operate the Docker-first deployment  
**When** I follow the backup runbook  
**Then** it provides concrete, step-by-step instructions to back up:
- the database (metadata),
- the object storage (file blobs), preserving the required bucket layout/prefixes so restores do not silently break previews/WOPI/media flows,
- and any locally-managed dev/test IdP fixtures if applicable,
and explicitly states what is out of scope / not required (e.g., ephemeral caches), without leaking secrets.

**Given** I need to restore from backups  
**When** I follow the restore runbook  
**Then** it provides concrete, step-by-step instructions to restore DB + object storage into a consistent state for the Docker-first baseline, including prerequisites and safety notes (no-leak).

**Given** a restore completed  
**When** I execute the post-restore smoke checklist  
**Then** it includes at least these deterministic checks (with expected outcomes):
- login succeeds (with an operator-provided external OIDC IdP; Keycloak only if used as a dev fixture),
- browse a workspace/folder succeeds,
- open an existing file preview works or shows a clear, actionable state (no infinite loading; no-leak),
- upload succeeds (or fails with an actionable no-leak error),
- media access via the `/media` flow succeeds (or fails with an actionable no-leak error referencing the edge contract).  
**And** if public share links are enabled for the environment, opening an existing share link works or shows a clear, actionable no-leak state.

## Tasks / Subtasks

- [ ] Write backup runbook (AC: 1)
  - [ ] DB backup steps (Postgres)
  - [ ] Object storage backup steps (bucket + required prefixes/layout)
  - [ ] Optional dev/test IdP fixture backup notes (Keycloak) if applicable
  - [ ] Explicit out-of-scope items (caches, ephemeral volumes)
- [ ] Write restore runbook (AC: 2)
  - [ ] DB restore steps
  - [ ] Object storage restore steps + validation notes
  - [ ] Safety notes and “no-leak” guidance
- [ ] Write deterministic post-restore smoke checklist (AC: 3)
  - [ ] Login
  - [ ] Browse
  - [ ] Preview
  - [ ] Upload
  - [ ] `/media` flow
  - [ ] Optional: public share link open
- [ ] Verification (doc quality)
  - [ ] Ensure steps are concrete, ordered, and proxy-agnostic.
  - [ ] Ensure no secrets are included in examples.

## Dev Notes

- The runbooks must match the Docker-first baseline (not Kubernetes procedures).
- Keep the checklist deterministic: explicit expected outcomes, no ambiguous “looks OK”.
- Reference the `/media` edge contract and audience model where relevant.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.4 Acceptance Criteria]
- [Source: `_bmad-output/project-context.md` — compose services, `/media` contract, and dev fixtures]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260210-212117-2.4/report.md`

### Completion Notes List

- Added a Docker-first backup/restore runbook covering Postgres + S3 bucket preservation.
- Included explicit no-leak guidance (avoid secrets, avoid signed URLs/SigV4).
- Added a deterministic post-restore smoke checklist (login/browse/preview/upload/media/share).

### File List

- `docs/installation/backup-restore.md`
- `docs/installation/README.md`
- `_bmad-output/implementation-artifacts/runs/20260210-212117-2.4/report.md`
