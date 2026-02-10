# Story 11.1: Drive-integrated CT-S3 runner with explicit audience model and deterministic reports

Status: review

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

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260210-212117-11.1/report.md`

### Completion Notes List

- Added `./bin/ct_s3` Docker-first entrypoint and `ct_s3` Django management command.
- Implemented audience-aware CT-S3 checks with explicit `INTERNAL_PROXY` vs `EXTERNAL_BROWSER` reporting.
- Encoded connect_url vs signed_host invariants using safe (hashed) evidence only.
- Wrote deterministic CT-S3 artifacts under `_bmad-output/implementation-artifacts/ct-s3/` with `latest.txt`.
- Documented execution and artifacts in `docs/ct-s3.md`.

### File List

- `bin/ct_s3`
- `docs/ct-s3.md`
- `docs/failure-class-glossary.md`
- `src/backend/core/ct_s3/__init__.py`
- `src/backend/core/ct_s3/constants.py`
- `src/backend/core/ct_s3/http_client.py`
- `src/backend/core/ct_s3/runner.py`
- `src/backend/core/ct_s3/safe.py`
- `src/backend/core/ct_s3/types.py`
- `src/backend/core/management/commands/ct_s3.py`
- `_bmad-output/implementation-artifacts/runs/20260210-212117-11.1/report.md`
