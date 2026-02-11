# Story 10.2: Capability-driven WOPI action exposure per backend (no dead buttons)

Status: in-progress

## Story

As an end user,
I want WOPI editing actions to appear only when the backend supports them and prerequisites are met,
So that the UI never offers a dead WOPI action.

## Acceptance Criteria

**Given** I browse files on S3 or a mount
**When** the API returns item/entry abilities
**Then** WOPI edit actions are exposed only when the integration is enabled & healthy and the backend-specific prerequisites are satisfied.
**And** when unavailable, the UI provides a clear “why + next action” state without leaking operator-only detail (Epic 5 patterns).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.2

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-235136-10.2/`
- Gates: `_bmad-output/implementation-artifacts/runs/20260211-235136-10.2/run-report.md`
- Commands: `_bmad-output/implementation-artifacts/runs/20260211-235136-10.2/commands.log`

### Completion Notes List

- Gated `is_wopi_supported` on WOPI enablement and backend support.
- Added deterministic WOPI init error codes and improved UI messaging.
- Kept abilities payload stable to avoid breaking non-WOPI behaviors.
- Updated retrieve API test to enable WOPI gating conditions.

### File List

- `src/backend/wopi/utils/__init__.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/items/test_api_items_wopi.py`
- `src/backend/wopi/tests/test_utils.py`
- `src/frontend/apps/drive/src/features/ui/preview/wopi/WopiEditor.tsx`
- `src/frontend/apps/drive/src/features/i18n/translations.json`
- `_bmad-output/implementation-artifacts/runs/20260211-222016-10.2/`
- `_bmad-output/implementation-artifacts/runs/20260211-230127-10.2/`
- `_bmad-output/implementation-artifacts/runs/20260211-235136-10.2/`
