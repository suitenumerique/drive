# Story 7.6 — Public MountProvider share-link semantics (404/410)

## Summary

Implemented public (unauthenticated) browse/open for MountProvider share links with
explicit 404 vs 410 semantics and no-leak operator diagnostics.

## What changed

- Added `GET /api/v1.0/mount-share-links/{token}/browse/`:
  - `404` for unknown/invalid token (generic response)
  - `410` for known token when the mount/target is missing (generic response)
- Ensured operator-facing log lines include deterministic `failure_class` and
  `next_action_hint`, plus allow-listed safe evidence only.
- Replaced path evidence with an HMAC-based `path_hash` (no raw `normalized_path`).
- Added a dedicated public frontend route for mount share links:
  - `GET /share/mount/{token}` with explicit “Link expired or target moved” state

## Verification

- Gates runner: see `run-report.md` (PASS) and `gates.md`.
- Unit tests added for 404/410 behavior and relative-path-only payloads.

## Notes / No-leak

- Public error responses are generic and do not include mount ids, SMB details,
  normalized paths, or stack traces.
