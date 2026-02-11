# Story 7.4: Enforce capability gating across mount actions (no dead actions, deterministic errors)

Status: ready-for-dev

## Story

As an end user,
I want mount actions (upload/download/preview/share/WOPI) to be gated by explicit capabilities and prerequisites,
So that unavailable actions are never presented as “clickable then fail”.

## Acceptance Criteria

**Given** a mount capability is false (e.g., `mount.preview=false`)
**When** the UI and API render/serve that action
**Then** the UI hides/disables the action with a clear, no-leak “why + next action” message, and the API rejects attempts deterministically without exposing provider internals.

**Given** a mount capability is true but a runtime prerequisite is missing/unhealthy
**When** the user attempts the action
**Then** the UI shows a time-bounded actionable state (per Epic 5.1) and the operator-facing surfaces expose `failure_class` + `next_action_hint` with safe evidence only.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.4

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


