# Story 4.2: Create folders in the explorer (capability-driven + clean validation)

Status: done

## Story

As an authenticated end user,
I want to create folders inside a workspace/folder,
So that I can organize my content.

## Acceptance Criteria

**Given** the user is authenticated and `abilities.children_create=true` on the target folder
**When** the user creates a folder with a title under that parent
**Then** the folder is created successfully and appears when listing the parent’s children.

**Given** the user is authenticated but `abilities.children_create=false` on the target folder
**When** the user attempts to create a folder
**Then** the request is rejected deterministically with a clean, no-leak error response (no stacktrace).

**Given** the folder name/title is invalid (e.g., missing or conflicting at the same level)
**When** the API validates the request
**Then** it returns a clean validation error (no-leak, no stacktrace) with stable error codes/messages.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.2

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260211-164716-4.2/run-report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-165142-4.2-no-leak/run-report.md`

### Completion Notes List
- Fix Explorer tree create-folder labels (capability-driven action surface).
- Add deterministic API coverage for children folder creation:
  - forbidden (`children_create=false`) returns clean `client_error`
  - missing title returns stable `validation_error` code
  - created folder is returned by children listing
- Verification recorded in run artifacts (gates PASS).

### File List
- `CHANGELOG.md`
- `src/frontend/apps/drive/src/features/explorer/components/tree/ExplorerTreeActions.tsx`
- `src/backend/core/tests/items/test_api_items_children_create.py`
- `src/backend/core/tests/items/test_api_items_list_ordering.py`
- `_bmad-output/implementation-artifacts/runs/20260211-164716-4.2/`
- `_bmad-output/implementation-artifacts/runs/20260211-165142-4.2-no-leak/`
