# Run Report — Story 1.1 (Canonical DRIVE_PUBLIC_URL)

- Run ID: `20260210-130620-1.1`
- Date (UTC): 2026-02-10T13:06:20Z
- Branch: `story/1.1-drive-public-url`

## Goal

Implement `DRIVE_PUBLIC_URL` + `DRIVE_ALLOW_INSECURE_HTTP` with strict deterministic validation/normalization and fail-fast behavior in `Base.post_setup`, with no-leak errors carrying stable `failure_class` + `next_action_hint`.

## Verification

- `make lint`: PASS
- Targeted tests (Story 1.1): PASS
  - `bin/pytest core/tests/test_settings.py core/tests/test_public_url.py -q`

## Notes

- This run supersedes `20260210-125506-1.1` by ensuring `make lint` is clean for the new files (docstrings) and by removing an incompatible pylint option (`suggestion-mode`) from `src/backend/.pylintrc`.
- Full suite (`make test-back`) is not re-run here; the prior run recorded unrelated pre-existing failures outside Story 1.1 scope.
