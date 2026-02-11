# Story 7.5: Create MountProvider share links for virtual entries (capability-driven)

Status: ready-for-dev

## Story

As an end user,
I want to create share links for MountProvider resources identified by `(mount_id, normalized_path)` when the mount supports it,
So that I can share mount content consistently with S3 sharing.

## Acceptance Criteria

**Given** a mount is configured and exposes the `mount.share_link` capability
**When** I request share link creation for a target `(mount_id, normalized_path)`
**Then** the system normalizes the path deterministically and stores a share-link token that maps to the virtual entry identifier.
**And** the public share URL is derived from `DRIVE_PUBLIC_URL`.

**Given** a mount does not expose the `mount.share_link` capability
**When** I attempt to create a share link for that mount
**Then** the API/UI behavior is capability-driven (no dead actions), and any client-facing error remains generic/no-leak.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.5

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


