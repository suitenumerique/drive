# Story 12.4: Wire CT-S3 and no-leak scanning into CI with strict scope; enforce dependency automation policy

Status: ready-for-dev

## Story

As a developer/CI,
I want CT-S3 and no-leak scanning wired into CI via stable gates with strict scanning scope,
So that v1 promises are enforced without noisy false positives or scope drift.

## Acceptance Criteria

**Given** `s3.contracts.seaweedfs` (or equivalent) gate is executed  
**When** the gates runner resolves it  
**Then** it invokes the CT-S3 suite delivered by Epic 11 and records results in deterministic artifacts.

**Given** no-leak scanning runs in CI  
**When** it evaluates generated artifacts  
**Then** automated scanning scope is limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) while preserving the global “no-leak everywhere” requirement.

**Given** `e2e.chrome` runs for scoped v1 flows  
**When** accessibility checks are executed (axe-based, “no regressions”)  
**Then** the run produces retained artifacts for the checked surfaces and fails deterministically with `failure_class` + `next_action_hint` on serious/critical violations, without leaking secrets or sensitive paths/keys.

**Given** dependency automation is configured  
**When** the repository automation is validated  
**Then** Renovate is the mechanism for version-bump PRs, and Dependabot is limited to security alerts only (no Dependabot PR configuration is introduced).

## Tasks / Subtasks

- [ ] Add CI wiring for CT-S3 gate(s) (AC: 1)
  - [ ] Ensure SeaweedFS baseline is the blocking profile.
  - [ ] Ensure artifacts are retained and deterministic.
- [ ] Add CI wiring for no-leak scanning with strict scope (AC: 2)
  - [ ] Limit scanning to `_bmad-output/**` text artifacts.
  - [ ] Ensure scanning output uses stable `failure_class` + `next_action_hint`.
- [ ] Add CI wiring for E2E chrome + axe smoke (AC: 3)
  - [ ] Retain artifacts for checked surfaces.
  - [ ] Fail deterministically on serious/critical a11y regressions.
- [ ] Enforce dependency automation policy (AC: 4)
  - [ ] Renovate allowed for version-bump PRs.
  - [ ] Dependabot restricted to security alerts (no PRs).

## Dev Notes

- This story depends on having CT-S3 and no-leak allow-listing delivered (Epic 11) and stable gate IDs (Story 12.1).
- Keep scanning scope strict to avoid false positives and prevent “scope creep”.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 12.4 Acceptance Criteria]
- [Source: `_bmad-output/implementation-artifacts/12-1-gates-runner-executes-stable-gate-ids-and-writes-deterministic-artifacts.md` — gate runner]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

