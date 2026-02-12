# Story 9.2 — SMB provider browse (list/stat)

## Summary

Implemented the SMB MountProvider browse contract (`stat` + `list_children`) with
normalized paths, deterministic ordering, and deterministic no-leak error
mapping.

## What changed

- Added `core.mounts.providers.smb` implementing:
  - `stat(mount, normalized_path)`
  - `list_children(mount, normalized_path)`
- Registered the provider as `provider: "smb"` in the mount registry.
- Added deterministic error mapping:
  - `mount.path.not_found` for missing paths
  - `mount.smb.env.*` classes for share/auth/connectivity failures
  - `mount.smb.{stat,list}_failed` for other operation failures
- Added unit tests covering ordering and failure mapping.

## Verification

- Backend gates runner: see `run-report.md` (PASS) and `gates.md`.

## Notes

- `make build-backend` was run to ensure the updated backend dependencies were
  present in the dev container before running the gates.
