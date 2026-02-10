# Run Report — Story 1.1 (Canonical `DRIVE_PUBLIC_URL`)

- Run ID: `20260210-125506-1.1`
- Date (UTC): 2026-02-10
- Branch: `story/1.1-drive-public-url`

## Goal

Implement `DRIVE_PUBLIC_URL` + `DRIVE_ALLOW_INSECURE_HTTP` with strict, deterministic validation/normalization and fail-fast behavior in `Base.post_setup`, using no-leak error messages that carry stable `failure_class` + `next_action_hint`.

## Implementation summary

- Added `core.utils.public_url.normalize_drive_public_url()` and `PublicUrlValidationError`.
- Added settings inputs in `src/backend/drive/settings.py`:
  - `DRIVE_PUBLIC_URL` (optional; rollout-safe when unset)
  - `DRIVE_ALLOW_INSECURE_HTTP` (dev-only override)
- Wired validation into `Base.post_setup`:
  - Normalizes trailing slash away (canonical base URL)
  - Rejects query/fragment/userinfo and non-empty paths (except `/`)
  - Enforces HTTPS in production posture (`DEBUG=False`) unless override is enabled
  - Raises a deterministic `ValueError` containing `failure_class=... next_action_hint=...` without echoing the raw URL

## Verification

See `commands.log` for full outputs.

- Targeted Story 1.1 tests: PASS (`core/tests/test_settings.py`, `core/tests/test_public_url.py`)
- `make lint`: PASS
- `make test-back`: executed, but the repo test suite failed with pre-existing failures outside the Story 1.1 scope (27 failing tests; 1090 passed in that run). Targeted Story 1.1 tests were re-run and passed.

## Failure classes introduced

- `config.public_url.invalid`
- `config.public_url.https_required`

