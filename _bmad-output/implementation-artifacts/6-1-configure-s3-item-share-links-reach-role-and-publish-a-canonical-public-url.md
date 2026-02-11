# Story 6.1: Configure S3 item share links (reach/role) and publish a canonical public URL

Status: done

## Story

As an end user,
I want to configure share link settings for an S3-backed file or folder and obtain a canonical share URL,
So that I can share access according to Drive’s sharing model.

## Acceptance Criteria

**Given** I am authenticated and have permission to share an S3-backed item
**When** I configure the item’s share link settings (reach and role) via the supported API/UI
**Then** the configuration is stored deterministically and returned in the item representation as share link state.
**And** the share URL is derived from `DRIVE_PUBLIC_URL` and uses the canonical public host.

**Given** I do not have permission to configure sharing on an item
**When** I attempt to change its share link settings
**Then** the API responds deterministically (no-leak) and the UI shows an actionable state (no dead actions), per Epic 5 patterns.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 6.1

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260211-202211-6.1/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-202211-6.1/run-report.md`

### Completion Notes List
- Expose canonical `share_url` for public link reach, derived from
  `DRIVE_PUBLIC_URL`.
- Add deterministic, unforgeable share tokens (HMAC) for item share URLs.
- Disable link reach/role controls when link configuration is not permitted.
- Gates: `backend.lint` PASS, `backend.tests` PASS, `frontend.lint` PASS,
  `docs.consistency` PASS, `no_leak.scan_bmad_output` PASS.

### File List
- `src/backend/core/api/serializers.py`
- `src/backend/core/tests/items/test_api_items_share_url.py`
- `src/backend/core/utils/share_links.py`
- `src/frontend/apps/drive/src/features/drivers/types.ts`
- `src/frontend/apps/drive/src/features/explorer/components/modals/share/ItemShareModal.tsx`
- `_bmad-output/implementation-artifacts/runs/20260211-202211-6.1/report.md`
