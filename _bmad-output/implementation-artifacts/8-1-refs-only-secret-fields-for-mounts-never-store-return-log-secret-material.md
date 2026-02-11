# Story 8.1: Refs-only secret fields for mounts (never store/return/log secret material)

Status: ready-for-dev

## Story

As an operator,
I want mount credentials to be expressed only as secret references (env var name and/or file path),
So that secret values are never stored in the database, returned by APIs, or leaked into logs/artifacts.

## Acceptance Criteria

**Given** a mount requires credentials
**When** the operator configures the mount
**Then** the configuration stores only references (e.g., `password_secret_ref` and/or `password_secret_path`), never secret values.
**And** secret references are not exposed on end-user APIs; they are provided only via operator-managed configuration (env/files) in v1 (no in-app admin UI in this project).

**Given** any mount-related API response, log line, or deterministic artifact is produced
**When** it includes mount configuration context
**Then** it never includes secret values and avoids leaking sensitive file paths; errors remain no-leak and generic for client-facing surfaces.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 8.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


