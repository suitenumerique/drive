# Failure Class Glossary (Deterministic)

This glossary defines a stable `failure_class` naming convention for operator-facing diagnostics and for test artifacts.

## Format

- `domain.category.reason` (lowercase, snake_case)

Each failure should also emit:

- `next_action_hint` (short, actionable)
- safe evidence only (status codes, request_id, hashes; never secrets/credentials/paths)

## Configuration — `config.*`

- `config.public_url.invalid`
- `config.public_url.https_required`

## S3 Contract Tests (CT-S3-*) — `s3.*`

- `s3.config.missing_env`
- `s3.config.bad_url`
- `s3.config.tls_strict_host_required`
- `s3.config.url_style_unsupported`
- `s3.drive.media_auth_http_403`
- `s3.drive.media_auth_http_non_200`
- `s3.signature.host_mismatch_internal`
- `s3.signature.host_mismatch_external`
- `s3.signature.security_token_not_forwarded`
- `s3.http.put_missing_required_header_x_amz_acl`
- `s3.http.range_not_206_strict` (optional strict check)
- `s3.http.copy_metadata_replace_not_applied`
- `s3.http.key_encoding_failed`
- `s3.net.connect_timeout`
- `s3.net.connect_refused`
- `s3.net.dns_failure`

## E2E (Playwright Chrome) — `e2e.*`

- `e2e.env.chrome_not_found`
- `e2e.env.base_url_unreachable`
- `e2e.env.keycloak_unreachable`
- `e2e.auth.login_failed`
- `e2e.test.timeout`
- `e2e.test.selector_unstable`

## Mounts / SMB — `mount.*`

- `mount.smb.env.unreachable`
- `mount.smb.env.auth_failed`
- `mount.smb.env.share_not_found`
- `mount.smb.list_failed`
- `mount.smb.stat_failed`
- `mount.smb.read_failed`
- `mount.smb.write_failed`
- `mount.smb.upload_timeout`
- `mount.smb.atomic_rename_failed`
- `mount.smb.range_unsupported`
