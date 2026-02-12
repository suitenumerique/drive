# Run report — 20260211-225555-10.1

Story file: `_bmad-output/implementation-artifacts/10-1-wopi-enablement-configuration-host-allowlist-https-posture-health-gating.md`

## Scope

- In: Fix WOPI settings tests to provide a public base URL when WOPI is enabled.
- Out: UI capability gating and WOPI launch flow changes (Stories 10.2/10.3).

## Changes

- Summary:
  - `wopi/tests/test_settings.py` now sets `DRIVE_PUBLIC_URL` in WOPI-enabled tests.
- Rationale:
  - Ensure the "missing discovery URL" test fails on discovery URL, not on
    `config.wopi.src_base_url.missing`.

## Verification

- Commands (via deterministic gates runner):
  - `make lint`
  - `make test-back`

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-225555-10.1/`
- Gates summary: see `run-report.md` / `gates.md`

## Follow-ups

- [ ]

