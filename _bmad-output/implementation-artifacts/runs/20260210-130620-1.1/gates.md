# Gates (manual, Story 1.1)

## backend.lint (PASS)

- `make lint`

## backend.tests.settings_public_url (PASS)

- `bin/pytest core/tests/test_settings.py core/tests/test_public_url.py -q`

## backend.tests.full (NON-BLOCKING / KNOWN-FAIL)

- Not re-run in this validation step.
- Prior run `20260210-125506-1.1` recorded unrelated pre-existing failures outside Story 1.1 scope.
