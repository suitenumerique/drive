# Story 4.5: Preview supported files via `/media/preview` (deterministic availability)

Status: done

## Story

As an authenticated end user,
I want to preview supported files,
So that I can quickly inspect content without downloading.

## Acceptance Criteria

**Given** a file is ready and previewable by backend rules
**When** the file is retrieved/listed
**Then** the API exposes a preview URL (`url_preview`) pointing to `/media/preview/...`.
**And** preview availability is deterministic and derived from backend rules (not UI heuristics).

**Given** the user opens the preview
**When** the browser requests `GET {url_preview}`
**Then** the preview is served successfully via the edge contract (auth subrequest + SigV4 propagation).
**And** the UI remains time-bounded/actionable per Epic 5.

**Given** a file is ready but not previewable by backend rules
**When** the file is retrieved/listed
**Then** `url_preview` is absent/null.
**And** the UI shows an explicit “preview not available” state (distinct from “access denied”), with no dead actions and no-leak messaging.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.5

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)


### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-183644-4.5/`


### Completion Notes List

- Preview availability is derived from backend `url_preview` (no UI heuristics).
- When `url_preview` is absent, the UI shows an explicit “preview not available”
  state with no dead actions.


### File List

- `_bmad-output/implementation-artifacts/runs/20260211-183644-4.5/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-183644-4.5/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260211-183644-4.5/files-changed.txt`
- `_bmad-output/implementation-artifacts/runs/20260211-183644-4.5/gates.md`
- `src/frontend/apps/drive/src/features/explorer/utils/utils.ts`
- `src/frontend/apps/drive/src/features/i18n/translations.json`
- `src/frontend/apps/drive/src/features/ui/preview/files-preview/FilesPreview.tsx`
- `src/frontend/apps/drive/src/features/ui/preview/not-supported/NotSupportedPreview.tsx`

