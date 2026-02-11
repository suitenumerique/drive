# Story 10.5: MountProvider WOPI semantics: version string + locks (TTL/release/conflict) + streaming save pipeline

Status: ready-for-dev

## Story

As an end user and operator,
I want WOPI on mounts to enforce deterministic version and lock semantics and stream saves back to the underlying provider,
So that collaborative editing is correct, efficient, and diagnosable without leaks.

## Acceptance Criteria

**Given** a mount exposes `mount.wopi=true`
**When** WOPI operations occur for that mount
**Then** the system computes a deterministic application-level version string that changes when content changes.

**Given** a WOPI session attempts to lock a mount-backed file
**When** a lock exists or expires
**Then** lock semantics are deterministic (TTL, release, conflict handling) and do not leak mount paths or credentials.

**Given** WOPI saves content back to a mount-backed file
**When** PutFile (or equivalent) is invoked
**Then** the backend streams the write through the provider (NFR1), and failures are surfaced as generic/no-leak to clients with operator-facing `failure_class` + `next_action_hint`.

## Epic 11: Storage Correctness Proof: CT-S3 (SeaweedFS Baseline, Audience-aware)

Developers/CI can run Drive-integrated S3 contract tests with explicit audiences; reports capture safe evidence without leaks; v1 supports SeaweedFS as the blocking baseline provider profile encoded as repeatable tests and runbook checks.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.5

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


