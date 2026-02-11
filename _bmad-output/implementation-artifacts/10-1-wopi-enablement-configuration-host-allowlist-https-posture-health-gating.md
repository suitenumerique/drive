# Story 10.1: WOPI enablement configuration (host allowlist, HTTPS posture, health gating)

Status: in-progress

## Story

As an operator,
I want to configure WOPI/Collabora integration with strict host allowlisting derived from `DRIVE_PUBLIC_URL` and clear health gating,
So that WOPI is safe-by-default and “enabled & healthy” is explicit and operator-debuggable.

## Acceptance Criteria

**Given** WOPI is enabled by configuration
**When** configuration validation runs
**Then** allowlisted WOPI hosts/origins are derived from `DRIVE_PUBLIC_URL` by default and are validated deterministically (no wildcards, no ambiguous parsing).
**And** production requires HTTPS for WOPI-related public surfaces (dev override only if explicitly enabled, consistent with Epic 1/2 TLS rules).

**Given** WOPI is enabled
**When** operator-facing diagnostics/health checks run
**Then** the system exposes an “enabled & healthy” vs “enabled but unhealthy” vs “disabled” state with `failure_class` + `next_action_hint` and allow-listed safe evidence only (no-leak).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


