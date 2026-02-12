# Story 10.4: S3 WOPI prerequisite validation (bucket versioning) with operator guidance

Status: done

## Story

As an operator,
I want S3 WOPI to be disabled when S3 prerequisites (e.g., bucket versioning) are not met, with clear guidance,
So that operators can remediate instead of debugging opaque runtime failures.

## Acceptance Criteria

**Given** WOPI is enabled but the S3 backend prerequisite is not satisfied
**When** the system evaluates backend prerequisites
**Then** WOPI is disabled for S3-backed files and operator-facing surfaces provide a deterministic `failure_class` + `next_action_hint` referencing the remediation steps.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.4

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-084105-10.4/commands.log`

### Completion Notes List
- Added deterministic S3 bucket versioning prerequisite check for WOPI.
- Surfaced `failure_class` + `next_action_hint` on operator-facing WOPI health.
- Verified: `make lint`, `make test-back` (PASS).

### File List
- `src/backend/wopi/services/s3_prerequisites.py`
- `src/backend/wopi/services/health.py`
- `src/backend/wopi/utils/__init__.py`
- `src/backend/wopi/tests/conftest.py`
- `src/backend/wopi/tests/services/test_health.py`
- `src/backend/core/tests/items/test_api_items_wopi.py`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-084105-10.4/report.md`
- `_bmad-output/implementation-artifacts/runs/20260212-084105-10.4/gates.md`
- `_bmad-output/implementation-artifacts/runs/20260212-084105-10.4/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260212-084105-10.4/files-changed.txt`
