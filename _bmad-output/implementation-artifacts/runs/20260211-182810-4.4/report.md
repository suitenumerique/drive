# Run report — Story 4.4 (Download via `/media` with Range support)

Story file: `_bmad-output/implementation-artifacts/4-4-download-files-via-media-edge-contract-range-support.md`

## Scope

- In: edge contract range pass-through for `/media/...` and `/media/preview/...`,
  and UI gating to avoid dead Download actions when no `url` is available.
- Out: end-to-end browser download verification (operator smoke checklist updated).

## Changes

- Nginx reference configs forward `Range` / `If-Range` and enable Range handling
  (`proxy_force_ranges on`) for deterministic partial content support.
- Docs:
  - Document Range expectations in `docs/selfhost/edge-contract.md`.
  - Add an operator smoke-check for Range responses in `docs/selfhost/smoke-checklist.md`.
- Frontend: hide Download action when the API does not expose `item.url`.

## Verification

Executed (UTC): 2026-02-11T18:28:10Z

- `docs.consistency`: PASS
- `frontend.lint` (`make frontend-lint`): PASS

See `run-report.md` / `run-report.json` for gate details.

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-182810-4.4/`
- Changed files list: `files-changed.txt`
- Commands log: `commands.log`

