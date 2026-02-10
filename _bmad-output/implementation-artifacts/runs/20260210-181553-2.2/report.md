# Run report — Story 2.2 (Nginx reference edge config for /media)

- Story file: _bmad-output/implementation-artifacts/2-2-nginx-reference-edge-configuration-dev-prod-aligned-for-media-auth-request-sigv4-propagation.md
- Branch: story/2.2-nginx-reference-edge
- PR: #10 (draft)
- Run folder: _bmad-output/implementation-artifacts/runs/20260210-181553-2.2

## Scope

- Align dev + prod Nginx reference configs for `/media/` and `/media/preview/`.
- Protect media routes with an auth subrequest to
  `GET /api/v1.0/items/media-auth/`.
- Forward all required SigV4 headers returned by `media-auth` to the upstream S3
  request, including optional `X-Amz-Security-Token` when present.
- Enforce no-leak defaults (never echo/log SigV4 secrets).

## Implementation summary

- Added explicit SigV4 header propagation from `media-auth`:
  `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`, `X-Amz-Security-Token`.
- Marked `/media-auth` as `internal` so it cannot be called directly by clients
  (prevents leaking SigV4 headers).
- Disabled `access_log` for `/media*` and `/media-auth` locations by default.
- Aligned prod config to include `/media/preview/` with the same contract as
  dev.

## Verification (Docker-first)

Evidence is recorded in `_bmad-output/implementation-artifacts/runs/20260210-181553-2.2/commands.log`.

- Nginx syntax check: `docker compose exec -T nginx nginx -t`.
- Smoke (download):
  - Direct S3 request without SigV4 headers returns `403`.
  - Same object via Nginx `/media/...` returns `200`.
- Smoke (preview where applicable):
  - A previewable PDF via Nginx `/media/preview/...` returns `200`.
- No-leak:
  - External call to `/media-auth` returns `404` (internal).
  - Run artifacts scanned for SigV4 signature material: no matches.
- Backend unit test (media-auth):
  - `core/tests/items/test_api_items_media_auth.py` passed under `Test`
    configuration with HTTPS-safe overrides for URL-like env vars.

## Files changed

See `_bmad-output/implementation-artifacts/runs/20260210-181553-2.2/files-changed.txt`.
