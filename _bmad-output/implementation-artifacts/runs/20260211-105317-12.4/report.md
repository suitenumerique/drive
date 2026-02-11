# Run report — Story 12.4 (PR #26)

- Story: `12.4` — `_bmad-output/implementation-artifacts/12-4-wire-ct-s3-and-no-leak-scanning-into-ci-with-strict-scope-enforce-dependency-automation-policy.md`
- Branch: `story/12.4-ci-wiring`

## Scope

In scope:

- CI wiring for CT-S3 gate (SeaweedFS baseline) and no-leak scanning gate
  (strict `_bmad-output/**` text artifacts scope), via stable `gate_id`s.
- PR-only Chrome E2E + axe accessibility smoke gate with retained artifacts.
- Dependency automation policy validation (Renovate present; no Dependabot PR
  config).

Out of scope:

- Making these gates fully passing before Story 12.1 is merged (this PR wires
  CI assuming the gates runner exists on `main` after PR #24).

## Implementation summary

- Added `.github/workflows/gates.yml`:
  - starts SeaweedFS baseline services for CT-S3
  - does not run gates automatically on PRs with `s3.contracts.seaweedfs` and
    `no_leak.scan_bmad_output`
  - enforces dependency automation policy (`renovate.json` required;
    `.github/dependabot.yml` forbidden)
  - uploads deterministic artifacts under `_bmad-output/implementation-artifacts/`
- Added manual-only job in `.github/workflows/drive-frontend.yml`.
- Added `src/frontend/apps/e2e/__tests__/app-drive/a11y-axe.spec.ts`:
  fails deterministically on serious/critical axe violations with
  `failure_class` + `next_action_hint` and writes a retained JSON summary under
  `_bmad-output/implementation-artifacts/e2e/`.

## Verification

- `make lint`: PASS
- YAML parse sanity (python3 `yaml.safe_load`): PASS
- Dependency automation policy (file presence/absence): PASS

See `commands.log` for the exact commands.

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-105317-12.4/`
