# Story 7.4: Enforce capability gating across mount actions (no dead actions, deterministic errors)

Status: review

## Story

As an end user,
I want mount actions (upload/download/preview/share/WOPI) to be gated by explicit capabilities and prerequisites,
So that unavailable actions are never presented as “clickable then fail”.

## Acceptance Criteria

**Given** a mount capability is false (e.g., `mount.preview=false`)
**When** the UI and API render/serve that action
**Then** the UI hides/disables the action with a clear, no-leak “why + next action” message, and the API rejects attempts deterministically without exposing provider internals.

**Given** a mount capability is true but a runtime prerequisite is missing/unhealthy
**When** the user attempts the action
**Then** the UI shows a time-bounded actionable state (per Epic 5.1) and the operator-facing surfaces expose `failure_class` + `next_action_hint` with safe evidence only.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.4

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)


### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-134613-7.4/`


### Completion Notes List
- Added capability-gated mount action endpoints (`preview`, `wopi`, `upload`)
  with deterministic no-leak errors.
- Added a basic mount browse UI and ensured mount actions are hidden when the
  mount capability is false, and disabled with “why + next action” messaging
  when capability is true but the runtime ability is unavailable.
- Added backend tests covering capability gating and deterministic errors.


### File List
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/mounts/test_api_mounts_actions_gating.py`
- `src/frontend/apps/drive/src/features/drivers/types.ts`
- `src/frontend/apps/drive/src/features/drivers/Driver.ts`
- `src/frontend/apps/drive/src/features/drivers/implementations/StandardDriver.ts`
- `src/frontend/apps/drive/src/pages/explorer/mounts/index.tsx`
- `src/frontend/apps/drive/src/pages/explorer/mounts/[mount_id].tsx`
- `src/frontend/apps/drive/src/features/i18n/translations.json`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-134613-7.4/`

