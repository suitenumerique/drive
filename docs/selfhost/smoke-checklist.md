# Smoke checklist (v1) — Docker-first, proxy-agnostic

This checklist is designed to be **deterministic** and **operator-run**.
It intentionally does not depend on any specific reverse proxy.

Perform these checks in order; each check must have a clear PASS/FAIL outcome.

## 0) Preflight configuration (deterministic)

Run one of:

- `python src/backend/manage.py config_preflight`
- `docker compose run --rm app-dev python manage.py config_preflight`

PASS:

- Exit code `0` and `ok=true`.

FAIL (expected shape):

- Exit code `1` with deterministic `errors[]` containing `failure_class` +
  `next_action_hint`.

Common failure classes:

- `config.s3.endpoint_url.missing`
- `config.s3.endpoint_url.invalid`
- `config.s3.domain_replace.invalid`
- `config.s3.domain_replace.https_required`

## 1) Login (OIDC)

- **Production:** use your operator-provided external OIDC IdP.
- **Development:** Keycloak is a fixture only.

Action:

- Log in and land in the Drive UI.

PASS:

- Explorer renders; no infinite loading; no mixed TLS modes.

## 2) Browse (workspace/folder)

Action:

- Open a known workspace/folder with existing content.

PASS:

- File list renders; navigation works.

## 3) Preview (existing file)

Action:

- Open preview for a known previewable file.

PASS:

- Preview renders, **or** shows a clear actionable state (no infinite loading;
  no-leak).

## 4) Upload (existing folder)

Action:

- Upload a small test file.

PASS:

- Upload completes and the file appears in the expected folder.

FAIL (acceptable):

- A clear actionable error that does not leak secrets.

## 5) Media access via `/media` (edge contract)

Action:

- Download/open an existing file that uses the `/media/...` flow through your
  reverse proxy.

PASS:

- The file loads successfully.

FAIL (acceptable):

- A clear actionable no-leak error that references the `/media` edge contract.
  See `docs/selfhost/edge-contract.md`.

## 6) Public share link (if enabled)

Action:

- Open an existing public share link in a private window.

PASS:

- Share opens, **or** shows a clear actionable state (no infinite loading;
  no-leak).

### Mount-backed share link semantics (MountProvider targets, if applicable)

If you test a mount-backed public share link:

- PASS: it respects the documented semantics:
  - `404` when the target cannot be found,
  - `410` when the share existed but the target is gone (out-of-band change).
