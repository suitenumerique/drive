# Story 4.4: Download files via `/media` (edge contract, Range support)

Status: done

## Story

As an authenticated end user,
I want to download files,
So that I can access my content outside the explorer.

## Acceptance Criteria

**Given** the user has access to a ready file (`upload_state != pending`)
**When** the file is retrieved/listed
**Then** the API exposes a download URL (`url`) pointing to the `/media/...` surface (not a raw S3 endpoint).

**Given** the user has access to the file
**When** the browser requests `GET {url}`
**Then** the file is served successfully via the edge contract (auth subrequest to `media-auth` + SigV4 header propagation), without requiring the browser to talk directly to S3.

**Given** the client issues an HTTP Range request to `{url}` (where applicable)
**When** the edge contract and storage backend support partial content
**Then** Range requests are supported deterministically (e.g., `206 Partial Content`), enabling large-file download/streaming behaviors.

**Given** the file is not ready (`upload_state=pending`) or the user is not allowed
**When** the browser requests `GET {url}` (or attempts to access `/media/...`)
**Then** access is denied with a clean, generic no-leak error for clients.
**And** operator-facing surfaces/diagnostics may provide actionable details via `failure_class` + safe evidence (no-leak).
**And** the UI follows Epic 5 patterns (actionable, no infinite loading).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.4

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-182810-4.4/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-182810-4.4/run-report.md`

### Completion Notes List

- Edge contract: forward `Range`/`If-Range` and force Range support in nginx
  reference configs for `/media` and `/media/preview`.
- UI: avoid dead Download actions by hiding Download when `item.url` is absent.
- Docs: update edge contract + smoke checklist with a deterministic Range check.
- Gates: `docs.consistency` PASS, `frontend.lint` PASS.

### File List

- `docker/files/development/etc/nginx/conf.d/default.conf`
- `src/nginx/servers.conf.erb`
- `docs/selfhost/edge-contract.md`
- `docs/selfhost/smoke-checklist.md`
- `src/frontend/apps/drive/src/features/explorer/components/item-actions/ItemActionDropdown.tsx`
- `_bmad-output/implementation-artifacts/runs/20260211-182810-4.4/report.md`
