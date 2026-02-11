# Story 12.3: Strict mirror enforcement (BMAD registry source-of-truth; GitHub fork mirror only)

Status: done

## Story

As a developer/CI,
I want strict mirror enforcement using a registry fingerprint (B+) embedded in issue/PR bodies,
So that GitHub remains a strict projection of BMAD local artifacts/registry and drift is blocked deterministically.

## Acceptance Criteria

**Given** a work item is mirrored into a GitHub issue/PR
**When** the fingerprint is computed and embedded
**Then** the fingerprint is computed from the canonical subset (B+) and excludes dynamic fields (status/runs/timestamps).

**Given** a PR is updated manually or diverges from the registry
**When** CI (and/or the runner) checks strict mirror integrity
**Then** it fails deterministically with `failure_class` + `next_action_hint` and clearly states that BMAD local artifacts/registry are the source of truth.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 12.3

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260211-205935-12.3/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-205935-12.3/run-report.md`

### Completion Notes List
- Add a B+ fingerprint function over canonical story sections (excludes dynamic
  fields like status/runs/timestamps and Dev Agent Record).
- Add a PR check that validates `BMAD-FP-BP: sha256:...` in PR bodies and fails
  deterministically with `failure_class` + `next_action_hint` on drift.
- Gates: `backend.lint` PASS, `backend.tests` PASS, `docs.consistency` PASS,
  `no_leak.scan_bmad_output` PASS.

### File List
- `.github/workflows/strict-mirror.yml`
- `bin/strict_mirror_check.py`
- `src/backend/core/tests/test_strict_mirror_fingerprint.py`
- `src/backend/core/utils/strict_mirror.py`
- `_bmad-output/implementation-artifacts/runs/20260211-205935-12.3/report.md`
