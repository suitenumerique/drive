# Run report — Story 2.1 (Docker-first edge contract)

Run key: 2.1

## Summary

- Added Docker-first self-host docs under `docs/selfhost/` (edge contract + smoke checklist).
- Added deterministic `config_preflight` management command to validate edge-related S3 inputs
  and emit a proxy-agnostic manual checklist (no live proxy inspection).
- Updated Nginx reference configs to forward optional `X-Amz-Security-Token` for SigV4.
- CI deblocking: Docker Hub builds no longer run on PRs; frontend e2e is skipped on PRs.

## Files changed

See `files-changed.txt`.

## Verification (dev-owned)

Per operator instruction, lint/tests/smoke are to be run by a developer and the results
recorded here.

- `make lint`: PENDING
- `make test-back`: PENDING
- `python src/backend/manage.py config_preflight`: PENDING
- `docker compose up -d` (infra smoke): PENDING

## Evidence / outputs

Paste command outputs here (no secrets, no signed URLs, no SigV4 headers).

## Non-blocking GitHub checks (ignore)

These checks are considered non-blocking for PR readiness in this fork:

- Docker Hub Workflow / build-and-push-backend
- Docker Hub Workflow / build-and-push-frontend
- Update crowdin sources / synchronize-with-crowdin
- Frontend Workflow / test-e2e (chromium/firefox/webkit)
