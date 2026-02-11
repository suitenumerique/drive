# Story 4.1: Browse workspaces and navigate folders (deterministic ordering + abilities contract)

Status: ready-for-dev

## Story

As an authenticated end user,
I want to browse my workspaces and navigate folders,
So that I can find and access my files.

## Acceptance Criteria

**Given** the user is authenticated and has app access (`can_access=true`)
**When** the user lists their accessible workspaces and opens a workspace/folder
**Then** the API returns the expected folder contents and metadata needed for navigation.
**And** ordering and pagination are deterministic (API is the source of truth; no UI-side sorting assumptions).
**And** listed items include the user-relevant `abilities` required by the Explorer to render actions without dead buttons (e.g., `children_list`, `children_create`, `media_auth`, `upload_ended`, plus other relevant action flags as applicable to the view).

**Given** the user is not authenticated
**When** they try to browse workspaces or folders
**Then** the API rejects the request with a clean authentication error (no-leak).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


