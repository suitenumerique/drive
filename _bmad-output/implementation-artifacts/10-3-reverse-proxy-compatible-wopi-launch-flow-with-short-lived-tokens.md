# Story 10.3: Reverse-proxy-compatible WOPI launch flow with short-lived tokens

Status: in-progress

## Story

As an end user,
I want to launch WOPI editing for an eligible file through a reverse-proxy-compatible flow,
So that WOPI works in self-host environments without direct internal network access.

## Acceptance Criteria

**Given** WOPI is enabled & healthy and a file is eligible
**When** I launch WOPI editing
**Then** the system issues a short-lived, no-leak WOPI access token and redirects/loads the WOPI client in a way compatible with reverse proxies.
**And** client-facing failures remain generic/no-leak; operator-facing surfaces provide `failure_class` + `next_action_hint`.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.3

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


