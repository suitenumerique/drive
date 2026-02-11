# Story 7.1: Operator-configured mounts registry (mount_id, provider, enabled) with deterministic validation

Status: ready-for-dev

## Story

As an operator,
I want to configure mounts with a stable `mount_id`, display name, provider type, and provider-specific non-secret parameters,
So that mounts can be managed without changing S3-backed behavior.

## Acceptance Criteria

**Given** the operator provides mount configuration inputs (settings/env/file-backed configuration)
**When** configuration validation runs
**Then** each mount has a stable, unique `mount_id`, a display name, a provider type, and provider-specific non-secret parameters.
**And** invalid configuration fails early with deterministic `failure_class` + `next_action_hint`, without leaking secrets or internal paths.

**Given** a mount is disabled
**When** users browse/discover mounts
**Then** the disabled mount is not available for end-user actions, and any attempted access yields deterministic, no-leak behavior.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


