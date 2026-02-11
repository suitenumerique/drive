# Story 9.1: SMB mount configuration schema and deterministic validation (refs-only secrets)

Status: ready-for-dev

## Story

As an operator,
I want to configure an SMB mount with explicit connection parameters and refs-only secrets,
So that SMB mounts are deployable in self-host environments without storing secrets in the database.

## Acceptance Criteria

**Given** an operator configures an SMB mount
**When** configuration validation runs
**Then** required fields are validated deterministically (at minimum: `server`, `share`, `username`; `port` defaultable; `domain/workgroup` optional; optional `base_path` and timeouts).
**And** password credentials are configured only via secret references per Epic 8 (refs-only; deterministic precedence).

**Given** invalid SMB configuration is provided
**When** validation runs
**Then** it fails early with deterministic `failure_class` + `next_action_hint`, with no-leak errors (no secret/path leaks).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 9.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


