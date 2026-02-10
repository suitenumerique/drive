# Gates (manual, Story 1.2)

## backend.lint (PASS)

- `make lint`

## backend.tests.allowlists (PASS)

- `pytest core/tests/test_settings.py core/tests/test_public_url.py core/tests/test_allowlists.py -q` (via `docker compose run --rm --no-deps app-dev`)
