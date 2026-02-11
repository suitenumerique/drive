# Story 10.4: S3 WOPI prerequisite validation (bucket versioning) with operator guidance

Status: ready-for-dev

## Story

As an operator,
I want S3 WOPI to be disabled when S3 prerequisites (e.g., bucket versioning) are not met, with clear guidance,
So that operators can remediate instead of debugging opaque runtime failures.

## Acceptance Criteria

**Given** WOPI is enabled but the S3 backend prerequisite is not satisfied
**When** the system evaluates backend prerequisites
**Then** WOPI is disabled for S3-backed files and operator-facing surfaces provide a deterministic `failure_class` + `next_action_hint` referencing the remediation steps.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.4

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


