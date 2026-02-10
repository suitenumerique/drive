# Run Report — Story 2.3 (TLS posture for public surfaces)

- Run ID: `20260210-141727-2.3`
- Date (UTC): 2026-02-10
- Branch: `story/1.1-drive-public-url`

## Goal

Enforce an HTTPS-only posture for public surfaces in production, with a centralized DEV-ONLY HTTP override and no mixed TLS modes, reusing the canonical public URL mechanism from Story 1.1.

## What changed

- Centralized public-surface base URL validation now enforces:
  - **Production posture (HTTPS-only)**: `http://` is rejected even if `DRIVE_ALLOW_INSECURE_HTTP=true`.
  - **Development posture**: `http://` is accepted only when `DEBUG=true` and `DRIVE_ALLOW_INSECURE_HTTP=true`.
- Extended validation to additional public surfaces:
  - `WOPI_SRC_BASE_URL` (when set)
  - URL-form entries in `OIDC_REDIRECT_ALLOWED_HOSTS` (when set)
  - `OIDC_REDIRECT_REQUIRE_HTTPS` is forced to `True` in HTTPS-only posture.
- Added a deterministic derivation helper `join_public_url()` to avoid double slashes in derived public-surface URLs.

## No-leak behavior

Validation failures are fail-fast and return deterministic `failure_class` + `next_action_hint` without echoing the raw input URL.

## Verification

See `commands.log`.

- `make lint`: PASS
- Targeted tests: PASS
  - `core/tests/test_settings.py`
  - `core/tests/test_public_url.py`
