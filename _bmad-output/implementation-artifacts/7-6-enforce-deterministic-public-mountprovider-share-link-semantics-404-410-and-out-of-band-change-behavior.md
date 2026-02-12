# Story 7.6: Enforce deterministic public MountProvider share-link semantics (404/410) and out-of-band change behavior

Status: review

## Story

As an end user and operator,
I want MountProvider public share links to have deterministic, no-leak semantics and explicit behavior for out-of-band target changes,
So that the public surface is safe and operationally diagnosable without exposing paths or SMB details.

## Acceptance Criteria

**Given** a public MountProvider share link is opened (unauthenticated recipient)
**When** the token is unknown/invalid
**Then** the response is `404` and remains generic/no-leak (no path, no SMB info, no stack traces).

**Given** a public MountProvider share link is opened (unauthenticated recipient)
**When** the token is valid/known but the target is missing (e.g., renamed/moved/deleted out-of-band)
**Then** the response is `410` and remains generic/no-leak (no path, no SMB info, no stack traces).
**And** the UI shows an explicit, actionable state (e.g., “Link expired or target moved”) without technical details, per Epic 5.

**Given** the operator inspects the failure via operator-facing surfaces (Diagnostics right panel and/or deterministic artifacts)
**When** the share link fails with `404` or `410`
**Then** operator-facing details include `failure_class` + `next_action_hint` and allow-listed safe evidence only.
**And** any mount path evidence uses `path_hash` (HMAC) rather than exposing `normalized_path`.

## Epic 8: Mount Secrets: Refs-only Resolution + Hot Rotation

Operators can reference secrets (ref/path) in mount configuration; the system resolves secrets at runtime without leaks, enforces refs-only semantics, deterministic precedence, and rotation without restart; session reuse across rotation is safe.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.6

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-151233-7.6/`

### Completion Notes List
- Added unauthenticated public browse endpoint for MountProvider share links with
  deterministic `404` (invalid token) vs `410` (known token, missing target)
  semantics and generic/no-leak responses.
- Added operator-facing log lines for `404/410` failures with deterministic
  `failure_class` + `next_action_hint` and allow-listed safe evidence only.
- Ensured mount path evidence uses HMAC-based `path_hash` (no raw mount paths).
- Added a dedicated public frontend route for mount share links that shows an
  explicit “Link expired or target moved” state on `410`.

### File List
- `src/backend/core/api/serializers_mounts.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/urls.py`
- `src/backend/core/utils/keyed_hash.py`
- `src/backend/core/tests/mounts/test_api_mount_share_links_public_browse.py`
- `src/frontend/apps/drive/src/pages/share/mount/[token].tsx`
- `_bmad-output/implementation-artifacts/runs/20260212-151233-7.6/`
