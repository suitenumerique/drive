# Run report — 20260211-222016-10.2

Story file: `_bmad-output/implementation-artifacts/10-2-capability-driven-wopi-action-exposure-per-backend-no-dead-buttons.md`

## Scope

- In: WOPI availability gating and user-facing failure messaging.
- Out: Short-lived token issuance and reverse-proxy launch flow (Story 10.3).

## Changes

- Summary:
  - Gate WOPI availability on integration enablement/config and backend support.
  - Emit deterministic error codes for WOPI init failures.
  - Show localized “why + next action” in the editor UI without operator leaks.
- Rationale:
  - Avoid offering WOPI actions that cannot work on the current backend.

## Verification

- Commands (via deterministic gates runner):
  - `make lint`
  - `make test-back`
  - `make frontend-lint`

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-222016-10.2/`
- Gates summary: see `run-report.md` / `gates.md`

## Follow-ups

- [ ] Ensure future UI action buttons consume the new WOPI init error codes.

