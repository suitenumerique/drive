# Story 10.2: Capability-driven WOPI action exposure per backend (no dead buttons)

Status: ready-for-dev

## Story

As an end user,
I want WOPI editing actions to appear only when the backend supports them and prerequisites are met,
So that the UI never offers a dead WOPI action.

## Acceptance Criteria

**Given** I browse files on S3 or a mount
**When** the API returns item/entry abilities
**Then** WOPI edit actions are exposed only when the integration is enabled & healthy and the backend-specific prerequisites are satisfied.
**And** when unavailable, the UI provides a clear “why + next action” state without leaking operator-only detail (Epic 5 patterns).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.2

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


