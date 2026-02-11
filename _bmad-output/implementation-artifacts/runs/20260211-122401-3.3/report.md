# Run report — Story 3.3

- Story: `3.3` — `_bmad-output/implementation-artifacts/3-3-external-api-allowlist-for-resources-and-actions-strict-no-wildcards.md`
- Branch: `story/3.3-external-api-allowlist`

## Scope

- Make external API resources truly allowlisted (resource-level enablement controls
  route exposure under `/external_api/v1.0/...`).
- Validate `EXTERNAL_API` configuration deterministically (strict, no wildcards)
  with stable `failure_class` + `next_action_hint`.

## Verification

- `make lint`: PASS
- Targeted tests: PASS (see `commands.log`)

