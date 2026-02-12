# Story 7.5: Create MountProvider share links for virtual entries (capability-driven)

Status: review

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
GPT-5.2 (Codex CLI)


### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-140328-7.5/`


### Completion Notes List
- Added `MountShareLink` model + migration to map share tokens to mount virtual
  entries `(mount_id, normalized_path)`.
- Implemented `POST /api/v1.0/mounts/{mount_id}/share-links/` gated by
  `mount.share_link`, with deterministic path normalization and
  `DRIVE_PUBLIC_URL`-derived share URLs.
- Updated mount browse UI to create and display mount share links when the
  capability is enabled.
- Added backend tests covering capability gating, path normalization, and
  idempotent token creation.


### File List
- `src/backend/core/models.py`
- `src/backend/core/migrations/0021_mount_share_link.py`
- `src/backend/core/api/serializers_mounts.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tests/mounts/test_api_mounts_share_links_create.py`
- `src/frontend/apps/drive/src/features/drivers/types.ts`
- `src/frontend/apps/drive/src/features/drivers/Driver.ts`
- `src/frontend/apps/drive/src/features/drivers/implementations/StandardDriver.ts`
- `src/frontend/apps/drive/src/pages/explorer/mounts/[mount_id].tsx`
- `src/frontend/apps/drive/src/features/i18n/translations.json`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-140328-7.5/`

