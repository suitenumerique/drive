# Run report — Story 4.1 (Browse workspaces and navigate folders)

Run key: 4.1

## Summary

- Browsing workspaces is authenticated-only: unauthenticated requests to
  `GET /api/v1.0/items/` return a clean 401 error.
- Ordering for workspace listing and folder children is deterministic and safe
  for pagination by always applying an `id` tie-breaker after the requested
  ordering fields.
- Item listings continue to include `abilities` for the Explorer to render
  actions without dead buttons (as validated by existing tests).

## Files changed

See `files-changed.txt`.

## Verification (dev-owned)

Executed (UTC): 2026-02-11T15:47:55Z

- `backend.lint` (`make lint`): PASS
- `backend.tests` (`make test-back`): PASS

See `run-report.md` / `run-report.json` for gate details.

## Evidence / outputs

- Gate runner report: `run-report.md`
- Gate results (machine-readable): `gates/gate-results.json`
