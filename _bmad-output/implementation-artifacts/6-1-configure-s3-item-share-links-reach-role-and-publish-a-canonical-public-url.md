# Story 6.1: Configure S3 item share links (reach/role) and publish a canonical public URL

Status: ready-for-dev

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


### Debug Log References


### Completion Notes List


### File List


