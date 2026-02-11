# Story 5.1: Time-bounded long-running operations (no infinite loading) with actionable fallback states

Status: ready-for-dev

## Story

As an end user and operator,
I want long-running/fragile operations to be time-bounded and to degrade into explicit actionable states,
So that the UI never spins indefinitely and users/operators always know what to do next.

## Acceptance Criteria

**Given** a long-running operation is in progress (v1 mandatory surfaces: upload flow (queue/progress + finalize), preview open, WOPI launch, public share-link open (S3 + mounts), and Diagnostics refresh (right panel))
**When** the UI is waiting for completion
**Then** it uses time thresholds that are per-operation (and configurable with documented defaults) and follows a consistent state progression: `loading` → `still working` (actionable) → `failed` (actionable), with no infinite spinner.

**Given** an upload is in progress
**When** the user navigates to another folder/workspace (within the same session)
**Then** the upload queue/progress remains visible and continues to update, and the user can return to the original context without losing the upload status (no infinite loading, actionable failure states).

**Given** an operation exceeds its configured threshold
**When** the UI transitions out of the initial loading state
**Then** it shows an explicit “still working” or “failed” state with a clear next action (retry / contact admin / runbook link), without leaking sensitive details.

**Given** an operation fails due to environment/proxy/storage conditions
**When** the UI displays the error
**Then** the messaging remains no-leak and capability-driven, and points to operator-facing diagnostics for actionable details.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 5.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


