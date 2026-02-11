# Story 5.3: Deterministic recovery patterns for uploads and media/edge failures (cleanup + actionable next steps)

Status: ready-for-dev

## Story

As an end user and operator,
I want deterministic recovery behavior for common operational failures (uploads, media access, proxy/auth subrequest),
So that users can retry safely and operators get actionable guidance without leaks.

## Acceptance Criteria

**Given** an upload fails due to a recoverable condition (e.g., expired presigned policy, temporary storage unavailability, proxy/media-auth failure)
**When** the failure is surfaced to the user
**Then** the UI shows an actionable, time-bounded error state per Epic 5.1 (retry / re-initiate upload / contact admin), with no-leak messaging.
**And** operator-facing surfaces provide `failure_class` + `next_action_hint` + allow-listed safe evidence (no-leak).

**Given** an upload attempt creates intermediate state (e.g., item created, `upload_state=pending`)
**When** the upload does not finalize (no `upload-ended`) within its documented time window (pending TTL)
**Then** the state transition is deterministic (e.g., pending → expired/failed) and the user sees an explicit, actionable state (no infinite loading).
**And** the item is not presented as ready and exposes no media/preview surfaces until finalized.

**Given** a user retries an upload after a failure
**When** the retry targets the same pending item (idempotent retry)
**Then** the system does not create a second “ghost” item implicitly; retries are idempotent or create additional items only in an explicitly visible and controlled way.
**And** recovery is deterministic: the user can retry safely or delete the pending item without ending up with duplicates or orphaned “ready-looking” entries.

**Given** media access fails through `/media` (edge contract)
**When** the user attempts to download/preview
**Then** the client-facing failure remains generic/no-leak.
**And** operator-facing diagnostics distinguish the audience model (e.g., `INTERNAL_PROXY` vs `EXTERNAL_BROWSER` as applicable) and provide actionable next steps (proxy contract checklist, CT-S3 pointers) without leaking secrets/paths/keys.

## Epic 6: Share Links (S3) with Public Token Access

Users can create share links for S3 items; public access is token-based and works without an authenticated session when configured as public.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 5.3

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


