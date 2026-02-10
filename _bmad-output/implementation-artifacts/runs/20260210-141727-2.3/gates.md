# Gates (manual, Story 2.3)

## backend.lint (PASS)

- `make lint`

## backend.tests.tls_posture (PASS)

- `pytest core/tests/test_settings.py core/tests/test_public_url.py -q` (via `docker compose run --rm --no-deps app-dev`)
