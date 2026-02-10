# Story 11.1: Drive-integrated CT-S3 runner with explicit audience model and deterministic reports

Status: ready-for-dev

## Story

As a developer/operator,
I want to run Drive-integrated S3 contract tests (CT-S3) with explicit audiences and deterministic reporting,
So that self-host deployments can prove the `/media` + SigV4 + upload/preview contracts against the supported S3 profiles.

## Acceptance Criteria

**Given** a target S3 provider profile is configured (SeaweedFS baseline in v1)  
**When** I run the CT-S3 suite via the documented entrypoint (local and CI)  
**Then** tests exercise the explicit audience model (`INTERNAL_PROXY` vs `EXTERNAL_BROWSER`) and validate the documented invariants (e.g., connect URL vs signed host expectations).  
**And** results are written as deterministic artifacts (human-readable + machine-readable) suitable for operator diagnostics.

## Tasks / Subtasks

- [ ] Define CT-S3 entrypoint(s) and gate identifiers (AC: 1)
  - [ ] Identify required provider profiles (SeaweedFS baseline, optional fixtures).
  - [ ] Decide report locations under `_bmad-output/implementation-artifacts/`.
- [ ] Implement audience-aware test harness (AC: 1)
  - [ ] Ensure tests explicitly distinguish `INTERNAL_PROXY` vs `EXTERNAL_BROWSER`.
  - [ ] Encode `connect_url` vs `signed_host` invariants in the runner output.
- [ ] Produce deterministic reports (AC: 1)
  - [ ] Human-readable summary
  - [ ] Machine-readable JSON (stable keys, stable ordering)
  - [ ] Stable “latest” pointer update
- [ ] Document how to run CT-S3 (AC: 1)
  - [ ] Docker-first instructions (baseline provider profile)
  - [ ] How to interpret artifacts and failure classes
- [ ] Verification (AC: 1)
  - [ ] At least one intentional failure scenario produces deterministic artifacts without leaks.

## Dev Notes

- CT-S3 is a Drive-integrated “contract proof” suite; avoid coupling to a single reverse proxy implementation.
- Outputs should be designed for operators (diagnostics) and CI (machine-readable), with no-leak constraints (see Story 11.3).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 11.1 Acceptance Criteria]
- [Source: `_bmad-output/project-context.md` — audience model, `/media` contract, connect_url vs signed_host]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

