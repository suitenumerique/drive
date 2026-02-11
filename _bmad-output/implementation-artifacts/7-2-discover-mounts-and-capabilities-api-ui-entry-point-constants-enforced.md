# Story 7.2: Discover mounts and capabilities (API + UI entry point, constants enforced)

Status: ready-for-dev

## Story

As an end user,
I want to discover the available mounts and their capabilities via an API and a UI entry point,
So that the Explorer can render mount surfaces and actions without dead buttons.

## Acceptance Criteria

**Given** mounts are configured
**When** I call the mounts discovery endpoint
**Then** the response includes `mount_id`, display name, provider type, and a capability map that uses the documented constant keys (at minimum: `mount.upload`, `mount.preview`, `mount.wopi`, `mount.share_link`).
**And** the response contains no secret material and does not expose SMB connection details.

**Given** the frontend renders the mounts entry point
**When** it displays mounts and actions
**Then** the UI is capability-driven (no dead actions) and uses Epic 5 messaging patterns for disabled/unavailable capabilities.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.2

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


