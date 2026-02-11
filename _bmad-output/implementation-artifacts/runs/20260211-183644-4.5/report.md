# Run report — Story 4.5 (Preview via `/media/preview`)

Run key: 4.5

## Summary

- UI preview availability is now determined by the backend-provided `url_preview`.
- When `url_preview` is absent, the UI shows an explicit “preview not available”
  state (distinct from access denied) and avoids dead preview actions.

## Files changed

See `files-changed.txt`.

## Verification (dev-owned)

Executed (UTC): 2026-02-11T18:36:44Z

- `frontend.lint` (`make frontend-lint`): PASS

See `run-report.md` / `run-report.json` for gate details.

## Evidence / outputs

- Gate runner report: `run-report.md`
- Gate results (machine-readable): `gates/gate-results.json`

