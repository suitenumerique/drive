# Story 7.5 — MountProvider share links for virtual entries

Implemented capability-driven share link creation for MountProvider virtual
entries identified by `(mount_id, normalized_path)`:

- Backend adds a `MountShareLink` mapping table and a `POST
  /api/v1.0/mounts/{mount_id}/share-links/` endpoint gated by
  `mount.share_link`.
- Paths are normalized deterministically and the response includes a canonical
  public share URL derived from `DRIVE_PUBLIC_URL`.
- Frontend mount browse UI can create/share links when capability is enabled.

## Evidence

- Gates runner report: `run-report.md` / `run-report.json`
- Commands: `commands.log`
- Files changed: `files-changed.txt`

