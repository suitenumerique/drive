# Gates (manual, Story 1.1)

## backend.tests.settings_public_url (PASS)

- `pytest core/tests/test_settings.py core/tests/test_public_url.py -q`

## backend.lint (PASS)

- `make lint`

## backend.tests.full (NON-BLOCKING / KNOWN-FAIL)

- `make test-back` currently fails in this workspace with unrelated failing tests.
- Story 1.1-specific tests pass.

