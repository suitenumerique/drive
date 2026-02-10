# Story 12.1: Gates runner executes stable `gate_id`s and writes deterministic artifacts

Status: ready-for-dev

## Story

As a developer/CI,
I want a gates runner that executes checks via stable `gate_id`s and writes deterministic artifacts,
So that CI and local runs produce consistent, machine-readable results with preserved evidence.

## Acceptance Criteria

**Given** a list of `gate_id`s is requested  
**When** the runner executes them  
**Then** it resolves `gate_id`s to the underlying commands deterministically and records `result`, `duration_ms`, and when failing `failure_class` + `next_action_hint`.  
**And** artifacts are written under `_bmad-output/implementation-artifacts/` in deterministic locations, including a stable “latest” pointer.

## Tasks / Subtasks

- [ ] Define the stable `gate_id` catalog and mapping rules (AC: 1)
  - [ ] Define IDs for backend lint/tests, CT-S3, no-leak scanning, docs consistency, mounts checks.
  - [ ] Ensure mapping is deterministic and versioned.
- [ ] Implement runner behavior (AC: 1)
  - [ ] Resolve gate IDs to commands deterministically.
  - [ ] Capture `duration_ms` and stable result codes.
  - [ ] On failure, emit `failure_class` + `next_action_hint` without leaking sensitive detail.
- [ ] Write deterministic artifacts (AC: 1)
  - [ ] Stable folder layout under `_bmad-output/implementation-artifacts/`.
  - [ ] Stable “latest” pointer update.
- [ ] Document usage (AC: 1)
  - [ ] How to request gates locally and in CI.
  - [ ] How to interpret artifact schema.

## Dev Notes

- Keep this small and deterministic: avoid dynamic output, timestamps in content, and non-stable ordering.
- This story is the foundation for wiring CT-S3 and no-leak scanning as stable gates (Story 12.4).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 12.1 Acceptance Criteria]
- [Source: `docs/agent-run-recording.md` — run artifact conventions (optional)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

