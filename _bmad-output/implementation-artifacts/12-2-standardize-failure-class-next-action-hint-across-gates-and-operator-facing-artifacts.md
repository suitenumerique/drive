# Story 12.2: Standardize `failure_class` + `next_action_hint` across gates and operator-facing artifacts

Status: review

## Story

As an operator/developer,
I want failures to be classified with stable `failure_class` values and actionable `next_action_hint`s,
So that troubleshooting is consistent across CT-S3, mounts integration checks, E2E, and mirror enforcement.

## Acceptance Criteria

**Given** any gate fails  
**When** artifacts are produced  
**Then** the artifact schema includes `failure_class` and `next_action_hint` as first-class fields and avoids embedding sensitive detail in the failure code itself.  
**And** evidence remains allow-listed and no-leak (Epic 11.3 / Epic 5.2).

## Tasks / Subtasks

- [ ] Define a stable schema for failure reporting (AC: 1)
  - [ ] Required fields: `failure_class`, `next_action_hint`, `audience` (where applicable), safe evidence.
  - [ ] Stable ordering and JSON schema if relevant.
- [ ] Align existing and planned artifacts to the schema (AC: 1)
  - [ ] CT-S3 artifacts
  - [ ] no-leak scanning artifacts
  - [ ] mounts-related checks artifacts
- [ ] Update docs taxonomy (AC: 1)
  - [ ] Ensure failure classes are documented and stable.

## Dev Notes

- Keep failure codes generic and non-sensitive; actionable detail belongs in allow-listed evidence and next-action hints.
- Prefer adding failure classes to `docs/failure-class-glossary.md` (if that remains the chosen location).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 12.2 Acceptance Criteria]
- [Source: `_bmad-output/implementation-artifacts/11-3-safe-evidence-allow-listing-for-ct-s3-no-leak-by-construction.md` — allow-listing intent]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-091933-12.2/report.md`

### Completion Notes List

- Documented a stable failure reporting schema (`failure_class`,
  `next_action_hint`, optional `audience`, safe evidence).
- Expanded `docs/failure-class-glossary.md` to include gate runner and no-leak
  scan failure classes.
- Added targeted backend tests locking CT-S3 result schema fields.

### File List

- `docs/failure-reporting-schema.md`
- `docs/failure-class-glossary.md`
- `src/backend/core/tests/test_ct_s3_failure_schema.py`
- `bin/pylint`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260211-091933-12.2/report.md`
