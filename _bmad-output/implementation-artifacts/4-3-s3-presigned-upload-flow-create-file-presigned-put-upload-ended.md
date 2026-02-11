# Story 4.3: S3 presigned upload flow (create file → presigned PUT → upload-ended)

Status: ready-for-dev

## Story

As an authenticated end user,
I want to upload files to S3-backed storage using a browser-compatible presigned flow,
So that I can add content reliably to my drive.

## Acceptance Criteria

**Given** the user is authenticated and `can_upload=true`
**When** the user creates a file entry and uploads the file using the returned presigned policy URL
**Then** the presigned URL is valid for the `EXTERNAL_BROWSER` audience and the browser can PUT the file to object storage.
**And** the backend upload finalization step (`upload-ended`) completes successfully.
**And** upload progress is visible and remains accessible while the user navigates to other folders/workspaces (no “lost upload” state), per Epic 5 resilience patterns.

**Given** `can_upload=false`
**When** the user attempts any upload-related operation
**Then** the operation is rejected with a clean, no-leak error (optionally using the safe entitlements message).
**And** any intermediate state is cleaned up deterministically (e.g., no orphaned “ready-looking” items in listings).

**Given** a presigned PUT upload fails before `upload-ended` is called
**When** the user refreshes the folder listing
**Then** the created item is not presented as ready (e.g., if it exists it remains `upload_state=pending`) and exposes no media/preview surfaces until finalized (concretely: no `url`/`url_preview`).
**And** any surfaced error follows Epic 5 patterns (actionable, no-leak, no infinite loading).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.3

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


