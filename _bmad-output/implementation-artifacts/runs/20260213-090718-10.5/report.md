# Story 10.5 — run 20260213-090718-10.5

- branch: story/10-5-mountprovider-wopi
- PR: #106 (draft)
- gates: PASS (`backend.lint`, `backend.tests`)
- runner: `bin/agent-check.sh --tag 10.5`

See `run-report.md` for the deterministic gate report.

## Completion notes

- Mount WOPI init (`/api/v1.0/mounts/{mount_id}/wopi/`) now issues a short-lived
  access token and launch URL for mount-backed files.
- Mount-backed WOPI endpoints (`/api/v1.0/wopi/mount-files/{file_id}/`) implement:
  - deterministic version string (`m1-<sha256_16>`) derived from size/modified_at
  - cache-backed locks with TTL and deterministic conflict handling
  - streaming PutFile saves to the provider (`open_write`) without buffering
- No-leak: mount paths are not echoed; operator logs use `path_hash`.
