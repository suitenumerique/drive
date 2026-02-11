# Story 3.2: Entitlements enforcement for access and uploads (API + UI gating)

Status: done

## Story

As an operator,
I want application access and capability policies to be enforced via an entitlements backend (e.g., `can_access`, `can_upload`) and exposed to the UI via an authenticated API,
So that I can restrict access and uploads deterministically without leaking sensitive information.

## Acceptance Criteria

**Given** an `ENTITLEMENTS_BACKEND` is configured
**When** an authenticated user requests `GET /api/v1.0/entitlements/`
**Then** the response contains at least `can_access` and `can_upload` entries with a boolean `result` and an optional safe `message` (no secret material, no internal URLs/paths/keys).

**Given** the entitlements backend returns `can_access.result=false` for a user
**When** the user attempts to authenticate via OIDC
**Then** authentication is denied with a clean, no-leak error response that is actionable for operators (safe message), and no authenticated session is established.

**Given** the entitlements backend returns `can_upload.result=false` for a user
**When** the user attempts any upload-related operation
**Then** the operation is denied with a clean, no-leak error response using the safe entitlements message (or a safe default).
**And** if an upload created intermediate state (e.g., a pending file item), it is cleaned up deterministically to avoid orphaned items.

**Given** the UI fetches entitlements for the current user
**When** `can_upload.result=false`
**Then** upload actions are hidden/disabled without dead buttons, and the user sees an explicit, no-leak explanation (using the safe entitlements message when available).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 3.2

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-121338-3.2/report.md`

### Completion Notes List

- Surfaced a safe entitlements message when OIDC access is denied (`can_access=false`).
- Added UI gating for uploads based on `GET /api/v1.0/entitlements/` (`can_upload`).

### File List

- `src/backend/core/authentication/views.py`
- `src/backend/core/tests/authentication/test_views.py`
- `src/frontend/apps/drive/src/features/entitlements/useEntitlementsQuery.ts`
- `src/frontend/apps/drive/src/features/explorer/hooks/useUpload.tsx`
- `src/frontend/apps/drive/src/features/explorer/components/app-view/AppExplorerBreadcrumbs.tsx`
- `_bmad-output/implementation-artifacts/runs/20260211-121338-3.2/report.md`
