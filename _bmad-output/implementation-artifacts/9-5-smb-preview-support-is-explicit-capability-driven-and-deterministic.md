# Story 9.5: SMB preview support is explicit, capability-driven, and deterministic

Status: ready-for-dev

## Story

As an end user,
I want preview behavior for SMB-backed files to be explicit and deterministic,
So that “preview not available” is distinct from “access denied” and the UI never relies on heuristics.

## Acceptance Criteria

**Given** an SMB mount exposes `mount.preview=true`
**When** I open a preview for a supported file
**Then** the backend serves preview content through the supported preview surface with deterministic behavior and no-leak errors.

**Given** an SMB mount does not expose `mount.preview` (or prerequisites are missing)
**When** I attempt to preview a file
**Then** the UI shows an explicit “preview not available” state (distinct from access denied) with a next action, per Epic 5.

## Epic 10: WOPI/Collabora Editing (Capability-driven, Enabled & Healthy)

WOPI actions appear only when prerequisites are met per backend; if S3 prerequisites (e.g., bucket versioning) are not met, WOPI is disabled with operator guidance; MountProvider WOPI uses app-level version string and lock semantics; users can launch WOPI editing via reverse-proxy-compatible flow; host allowlist derives from `DRIVE_PUBLIC_URL`; edits save back through the supported write pipeline.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 9.5

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


