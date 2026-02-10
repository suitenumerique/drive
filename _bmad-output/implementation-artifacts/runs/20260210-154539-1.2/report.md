# Run Report — Story 1.2 (Split allowlists derived from `DRIVE_PUBLIC_URL`)

- Run ID: `20260210-154539-1.2`
- Date (UTC): 2026-02-10
- Branch: `story/1.2-allowlists`

## Goal

Split operator-facing allowlists by purpose (redirect URIs vs origins vs hosts), always include canonical defaults derived from `DRIVE_PUBLIC_URL`, and wire final validated lists into the concrete consumers:

- OIDC `returnTo` safety: `OIDC_REDIRECT_ALLOWED_HOSTS` / `OIDC_REDIRECT_REQUIRE_HTTPS`
- SDK relay CORS: `SDK_CORS_ALLOWED_ORIGINS`

All validation must be deterministic, fail-fast, no-leak, and reuse the centralized TLS posture rules (Story 2.3).

## Consumer mapping (concrete)

- OIDC redirect safety is enforced by `mozilla_django_oidc.views.get_next_url()` using `url_has_allowed_host_and_scheme()` with:
  - `allowed_hosts = OIDC_REDIRECT_ALLOWED_HOSTS + [request.get_host()]`
  - `require_https = OIDC_REDIRECT_REQUIRE_HTTPS`
  Therefore, `OIDC_REDIRECT_ALLOWED_HOSTS` must be **host[:port]** only (not origins/URLs).
- SDK relay CORS is enforced in `core.api.viewsets.SDKRelayEventViewset.handle_cors()` by strict string match on the `Origin` header against `SDK_CORS_ALLOWED_ORIGINS`.

## What changed

- Added deterministic allowlist validators/normalizers (`core.utils.allowlists`):
  - redirect URIs: absolute http(s) URI incl. path, no wildcards, no query/fragment/userinfo
  - origins: origin form only (scheme+host[:port]), no wildcards
  - hosts: host[:port] only, no wildcards
  - fail-fast errors carry stable `failure_class` + `next_action_hint` without echoing raw values
- Added new operator-facing env vars (additive; canonical defaults always included when `DRIVE_PUBLIC_URL` is set):
  - `DRIVE_ALLOWED_REDIRECT_URIS`
  - `DRIVE_ALLOWED_ORIGINS`
  - `DRIVE_ALLOWED_HOSTS`
- Wiring in `Base.post_setup`:
  - derives canonical origin/host/root-redirect from `DRIVE_PUBLIC_URL`
  - merges + normalizes + dedupes (deterministic order)
  - applies:
    - `OIDC_REDIRECT_ALLOWED_HOSTS` (hosts derived from canonical + redirect URIs + host allowlist + legacy entries)
    - `SDK_CORS_ALLOWED_ORIGINS` (canonical origin + origin allowlist + legacy entries)

## Verification

See `commands.log`.

- `make lint`: PASS
- Targeted tests: PASS
  - `core/tests/test_settings.py`
  - `core/tests/test_public_url.py`
  - `core/tests/test_allowlists.py`
