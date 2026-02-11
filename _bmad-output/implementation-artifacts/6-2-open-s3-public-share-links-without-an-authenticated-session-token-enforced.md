# Story 6.2: Open S3 public share links without an authenticated session (token-enforced)

Status: done

## Story

As an end user,
I want to open a public share link for an S3-backed file or folder without an authenticated session,
So that sharing works for recipients who are not logged into Drive.

## Acceptance Criteria

**Given** a share link is configured as public
**When** a recipient opens the share URL in a browser without being authenticated
**Then** access is enforced by the share token and the recipient can view the shared content within the configured reach/role.
**And** the share experience is time-bounded and actionable (no infinite loading) per Epic 5.1.

**Given** a share link is not public (or sharing is disabled)
**When** an unauthenticated recipient opens the share URL
**Then** the client response is generic/no-leak and does not reveal the item’s existence or metadata beyond the intended behavior.

## Epic 7: MountProvider Framework: Contract-level Browse/Discover + Capability Gating

Framework epic (contract-level): configure mounts, enable/disable without impacting S3, discover mounts/capabilities, browse with deterministic ordering/pagination, enforce capability gating (no dead actions), and support MountProvider share links with deterministic semantics when capability is enabled.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 6.2

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260211-204733-6.2/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-204733-6.2/run-report.md`

### Completion Notes List
- Add token-enforced public share browse API: `share-links/:token/browse/`.
- Add unauthenticated public share page: `/share/:token`.
- Enforce `share_token` for unauthenticated `/media` access via `media-auth`.
- Gates: `backend.lint` PASS, `backend.tests` PASS, `frontend.lint` PASS,
  `docs.consistency` PASS, `no_leak.scan_bmad_output` PASS.

### File List
- `src/backend/core/api/serializers_share_links.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/items/test_api_items_media_auth.py`
- `src/backend/core/tests/share_links/test_api_share_links_browse.py`
- `src/backend/core/urls.py`
- `src/backend/core/utils/share_links.py`
- `src/frontend/apps/drive/src/pages/share/[token].tsx`
- `_bmad-output/implementation-artifacts/runs/20260211-204733-6.2/report.md`
