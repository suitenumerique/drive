# Story 9.2: SMB provider implements the mount browse contract (list/stat) with deterministic ordering

Status: ready-for-dev

## Story

As a user,
I want SMB-backed mounts to support directory listing and metadata lookup through the MountProvider interface,
So that the Epic 7 browse endpoints can work without SMB-specific endpoints or duplicated browse implementations.

## Acceptance Criteria

**Given** an SMB mount is enabled
**When** a mount browse request is executed through the provider interface
**Then** the provider returns directory entries with deterministic ordering and normalized paths.
**And** provider errors are mapped to deterministic, no-leak failures (no raw stack traces, no credential leaks, no raw SMB path leaks).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 9.2

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


