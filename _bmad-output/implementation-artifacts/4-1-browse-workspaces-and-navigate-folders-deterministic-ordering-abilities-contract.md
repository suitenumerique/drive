# Story 4.1: Browse workspaces and navigate folders (deterministic ordering + abilities contract)

Status: done

## Story

As an authenticated end user,
I want to browse my workspaces and navigate folders,
So that I can find and access my files.

## Acceptance Criteria

**Given** the user is authenticated and has app access (`can_access=true`)
**When** the user lists their accessible workspaces and opens a workspace/folder
**Then** the API returns the expected folder contents and metadata needed for navigation.
**And** ordering and pagination are deterministic (API is the source of truth; no UI-side sorting assumptions).
**And** listed items include the user-relevant `abilities` required by the Explorer to render actions without dead buttons (e.g., `children_list`, `children_create`, `media_auth`, `upload_ended`, plus other relevant action flags as applicable to the view).

**Given** the user is not authenticated
**When** they try to browse workspaces or folders
**Then** the API rejects the request with a clean authentication error (no-leak).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.1

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- Gate run: `_bmad-output/implementation-artifacts/runs/20260211-154755-4.1/run-report.md`
- Gate results: `_bmad-output/implementation-artifacts/runs/20260211-154755-4.1/gates/gate-results.json`

### Completion Notes List
- Enforced authenticated-only workspace listing (`GET /api/v1.0/items/` returns 401
  when unauthenticated).
- Made list/children ordering deterministic by always adding an `id` tie-breaker
  to the requested ordering, ensuring stable pagination boundaries.
- Added/updated tests for anonymous list auth and ordering determinism.
- Kept SeaweedFS baseline green by porting the S3 `CopyObject` GET→PUT fallback
  and updating presign URL tests to assert the configured region.

### File List
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/backend/core/api/permissions.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/items/test_api_items_list.py`
- `src/backend/core/tests/items/test_api_items_list_ordering.py`
- `src/backend/core/tests/items/test_api_items_children_ordering.py`
- `src/backend/core/tests/items/test_api_items_create.py`
- `src/backend/core/tests/items/test_api_items_children_create.py`
- `_bmad-output/implementation-artifacts/runs/20260211-154755-4.1/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-154755-4.1/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260211-154755-4.1/files-changed.txt`
- `_bmad-output/implementation-artifacts/runs/20260211-154755-4.1/gates.md`
