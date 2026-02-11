# Run report — 20260211-222743-10.3

Story file: `_bmad-output/implementation-artifacts/10-3-reverse-proxy-compatible-wopi-launch-flow-with-short-lived-tokens.md`

## Scope

- In: Reverse-proxy-compatible WOPI launch and time-bounded token issuance.
- Out: Collabora/OnlyOffice vendor-specific hardening beyond WOPISrc building.

## Changes

- Summary:
  - Build absolute `WOPISrc` using `WOPI_SRC_BASE_URL`, `DRIVE_PUBLIC_URL`, or request base URL.
  - Allow per-request override of the WOPI source base when generating the launch URL.
  - Shorten default WOPI access token TTL and sync env docs.
- Rationale:
  - Ensure WOPI launch works behind reverse proxies without relying on internal hostnames.

## Verification

- Commands (via deterministic gates runner):
  - `make lint`
  - `make test-back`

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-222743-10.3/`
- Gates summary: see `run-report.md` / `gates.md`

## Follow-ups

- [ ] Confirm recommended TTL defaults with product/security owners.

