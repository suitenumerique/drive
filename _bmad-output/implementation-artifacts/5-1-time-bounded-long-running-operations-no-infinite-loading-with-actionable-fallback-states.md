# Story 5.1: Time-bounded long-running operations (no infinite loading) with actionable fallback states

Status: done

## Story

As an end user and operator,
I want long-running/fragile operations to be time-bounded and to degrade into explicit actionable states,
So that the UI never spins indefinitely and users/operators always know what to do next.

## Acceptance Criteria

**Given** a long-running operation is in progress (v1 mandatory surfaces: upload flow (queue/progress + finalize), preview open, WOPI launch, public share-link open (S3 + mounts), and Diagnostics refresh (right panel))
**When** the UI is waiting for completion
**Then** it uses time thresholds that are per-operation (and configurable with documented defaults) and follows a consistent state progression: `loading` → `still working` (actionable) → `failed` (actionable), with no infinite spinner.

**Given** an upload is in progress
**When** the user navigates to another folder/workspace (within the same session)
**Then** the upload queue/progress remains visible and continues to update, and the user can return to the original context without losing the upload status (no infinite loading, actionable failure states).

**Given** an operation exceeds its configured threshold
**When** the UI transitions out of the initial loading state
**Then** it shows an explicit “still working” or “failed” state with a clear next action (retry / contact admin / runbook link), without leaking sensitive details.

**Given** an operation fails due to environment/proxy/storage conditions
**When** the UI displays the error
**Then** the messaging remains no-leak and capability-driven, and points to operator-facing diagnostics for actionable details.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 5.1

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- Gate run: `_bmad-output/implementation-artifacts/runs/20260211-153447-5.1/run-report.md`
- Gate results: `_bmad-output/implementation-artifacts/runs/20260211-153447-5.1/gates/gate-results.json`

### Completion Notes List
- Added per-operation time bounds with consistent UI states:
  `loading` → `still working` → `failed` (with Retry) for config load, upload
  flow, PDF preview, and WOPI launch.
- Added backend-configurable overrides via `FRONTEND_OPERATION_TIME_BOUNDS_MS`
  and merged them at runtime on the frontend.
- Ensured no-leak messaging for upload failures (no signed URLs in errors).
- Docker-first: `make frontend-lint` now runs in compose `node` service.
- SeaweedFS baseline compatibility: added S3 `CopyObject` fallback (GET→PUT)
  for content-type updates and fixed tests to use configured S3 region.

### File List
- `Makefile`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/backend/drive/settings.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/test_api_config.py`
- `src/backend/core/tests/items/test_api_items_children_create.py`
- `src/backend/core/tests/items/test_api_items_create.py`
- `src/frontend/apps/drive/src/features/api/fetchApi.ts`
- `src/frontend/apps/drive/src/features/config/ConfigProvider.tsx`
- `src/frontend/apps/drive/src/features/config/runtimeConfig.ts`
- `src/frontend/apps/drive/src/features/drivers/implementations/StandardDriver.ts`
- `src/frontend/apps/drive/src/features/drivers/types.ts`
- `src/frontend/apps/drive/src/features/explorer/components/toasts/FileUploadToast.tsx`
- `src/frontend/apps/drive/src/features/i18n/translations.json`
- `src/frontend/apps/drive/src/features/operations/timeBounds.ts`
- `src/frontend/apps/drive/src/features/operations/useTimeBoundedPhase.ts`
- `src/frontend/apps/drive/src/features/ui/preview/pdf-preview/PreviewPdf.tsx`
- `src/frontend/apps/drive/src/features/ui/preview/wopi/WopiEditor.tsx`
- `_bmad-output/implementation-artifacts/runs/20260211-153447-5.1/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-153447-5.1/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260211-153447-5.1/files-changed.txt`
- `_bmad-output/implementation-artifacts/runs/20260211-153447-5.1/gates.md`
