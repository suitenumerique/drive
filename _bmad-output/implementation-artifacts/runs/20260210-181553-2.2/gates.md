# Gates (manual, Story 2.2)

Note: the `drive-gates-runner` skill references `bin/agent-check.sh`, but that
script is not present in this workspace, so gates were executed manually and
recorded in `commands.log`.

## nginx.config.test (PASS)

- `docker compose exec -T nginx nginx -t`

## docker.smoke.media (PASS)

- Direct S3 access without SigV4 headers returns `403` (expected).
- `/media/<file_key>` via Nginx returns `200` and includes
  `Content-Disposition: attachment`.

## docker.smoke.media_preview (PASS)

- `/media/preview/<file_key>` via Nginx returns `200` for a previewable PDF.

## no_leak.media_auth_internal (PASS)

- `/media-auth` returns `404` when called externally (Nginx `internal`).
- Nginx logs scanned for `Authorization` / `x-amz-*` signature material: no
  matches.

## backend.tests.media_auth (PASS)

- `docker compose run --rm --user <uid:gid> -e DJANGO_CONFIGURATION=Test \
    -e WOPI_SRC_BASE_URL=https://drive.example.invalid \
    -e OIDC_REDIRECT_ALLOWED_HOSTS=localhost:8083,localhost:3000 \
    app-dev pytest core/tests/items/test_api_items_media_auth.py -q`

