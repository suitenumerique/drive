# Story 7.2: Discover mounts and capabilities (API + UI entry point, constants enforced)

Status: done

## Story

As an end user,
I want to discover the available mounts and their capabilities via an API and a UI entry point,
So that the Explorer can render mount surfaces and actions without dead buttons.

## Acceptance Criteria

**Given** mounts are configured
**When** I call the mounts discovery endpoint
**Then** the response includes `mount_id`, display name, provider type, and a capability map that uses the documented constant keys (at minimum: `mount.upload`, `mount.preview`, `mount.wopi`, `mount.share_link`).
**And** the response contains no secret material and does not expose SMB connection details.

**Given** the frontend renders the mounts entry point
**When** it displays mounts and actions
**Then** the UI is capability-driven (no dead actions) and uses Epic 5 messaging patterns for disabled/unavailable capabilities.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.2

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-101451-7.2/`

### Completion Notes List
- Updated mounts discovery endpoint to return a no-leak schema with a capability
  map keyed by contract constants.
- Added `/explorer/mounts` UI entry point wired to discovery and capability
  rendering (no dead actions).
- Added backend helper to normalize/enforce capability keys.
- Updated backend tests for the new discovery schema and no-leak constraints.

### File List
- `src/backend/core/services/mount_capabilities.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/mounts/test_api_mounts.py`
- `src/frontend/apps/drive/src/features/mounts/constants.ts`
- `src/frontend/apps/drive/src/features/drivers/Driver.ts`
- `src/frontend/apps/drive/src/features/drivers/types.ts`
- `src/frontend/apps/drive/src/features/drivers/implementations/StandardDriver.ts`
- `src/frontend/apps/drive/src/utils/defaultRoutes.ts`
- `src/frontend/apps/drive/src/pages/explorer/mounts/index.tsx`
- `src/frontend/apps/drive/src/features/i18n/translations.json`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-101451-7.2/`
