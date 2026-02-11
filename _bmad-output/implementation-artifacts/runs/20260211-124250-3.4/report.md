# Run report — Story 3.4 (PR #35)

- Story: `3.4` — `_bmad-output/implementation-artifacts/3-4-resource-server-mode-external-api-is-disabled-by-default-and-token-authenticated.md`
- PR: #35
- Branch: `story/3.4-resource-server-default-off`

## Scope

In scope:

- External API routes remain hidden unless explicitly enabled.
- Requests without a bearer token (or with invalid/expired tokens) fail with
  clean 401 responses and generic, no-leak error details.
- Valid bearer tokens with non-allowlisted audiences are rejected
  deterministically with 403.
- OIDC RS introspection secret follows refs-only configuration (file/env ref)
  and never accepts direct secret material via `OIDC_RS_CLIENT_SECRET`.

Out of scope:

- Per-resource allowlist normalization and strict validation (Story 3.3).

## Implementation summary

- Gate external API routes under `EXTERNAL_API` enablement.
- Use a wrapper authenticator to sanitize authentication errors.
- Switch `OIDC_RS_CLIENT_SECRET` to refs-only resolution.
- Update docs and add/adjust tests for the external API surface.

## Verification

- `make lint`: PASS
- `bin/pytest src/backend/core/tests/external_api -q`: PASS

See `commands.log` for the exact commands.

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/`
