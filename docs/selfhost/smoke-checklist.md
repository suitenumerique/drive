# Smoke checklist (v1) — Docker-first, proxy-agnostic

This checklist is designed to be **deterministic** and **operator-run**.
It intentionally does not depend on any specific reverse proxy.

## 0) Preflight configuration (deterministic)

Run:

- `python src/backend/manage.py config_preflight`

Expected:

- Exit code `0` and `ok=true`, or exit code `1` with deterministic `errors[]`.

Common failure classes:

- `config.s3.endpoint_url.missing`
- `config.s3.endpoint_url.invalid`
- `config.s3.domain_replace.invalid`
- `config.s3.domain_replace.https_required`

## 1) Auth (dev vs prod)

- **Production:** bring your own OIDC provider.
- **Development:** Keycloak is a fixture only.

Expected:

- You can log in and reach the Drive UI without mixed TLS modes.

## 2) Basic navigation

Expected:

- You can browse a workspace and folders.

## 3) Upload (EXTERNAL_BROWSER)

Expected:

- A browser upload succeeds using a presigned PUT.
- If uploads fail with `403`, check the **signed host** and whether your browser is
  using `AWS_S3_DOMAIN_REPLACE` (when set).

## 4) Media download via `/media` (INTERNAL_PROXY)

Expected:

- Downloading a file via `/media/...` succeeds through your reverse proxy.

If you observe `403 SignatureDoesNotMatch` from the S3 upstream:

- Verify the proxy forwards SigV4 headers from the auth subrequest response:
  - `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`
  - `X-Amz-Security-Token` when using temporary credentials
- Verify the upstream **Host** header matches `AWS_S3_ENDPOINT_URL`.

## 5) Media preview via `/media/preview` (INTERNAL_PROXY)

Expected:

- Preview media (when applicable) is fetched via `/media/preview/...` and authorized
  by the same `media-auth` contract.

