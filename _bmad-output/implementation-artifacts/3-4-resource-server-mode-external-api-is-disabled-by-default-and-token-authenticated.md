# Story 3.4: Resource Server mode (external API) is disabled-by-default and token-authenticated

Status: review

## Story

As an integrator,
I want Drive to expose a dedicated external API surface as an OIDC Resource Server when explicitly enabled,
So that a suite service can call approved routes using bearer tokens without relying on the internal user session API.

## Acceptance Criteria

**Given** Resource Server mode is disabled
**When** a client calls any `/external_api/v1.0/...` endpoint
**Then** the server returns `404` (routes are not exposed).

**Given** Resource Server mode is enabled by explicit operator configuration
**When** a client calls a permitted `/external_api/v1.0/...` endpoint without a bearer token (or with an invalid/expired token)
**Then** the request is rejected with `401` and a clean, no-leak authentication error that remains generic for clients (do not leak introspection details).
**And** actionable details are reserved for operator-facing surfaces/diagnostics only (no-leak).

**Given** Resource Server mode is enabled and a bearer token is accepted as valid
**When** the token client identity/audience is not in the operator allowlist
**Then** the request is rejected deterministically with a documented status code (v1: `403`), and remains no-leak and generic for clients (do not expose token claims or rejection reasons).
**And** actionable details are reserved for operator-facing surfaces/diagnostics only (no-leak).

**Given** Resource Server mode is enabled
**When** bearer token validation is performed
**Then** it uses an introspection-based validation flow (not JWT-only), consistent with the configured OIDC OP endpoints.

**Given** Resource Server mode is enabled and a client secret is required for token introspection
**When** secret configuration is provided
**Then** it follows the refs-only pattern (env var ref and/or file path ref with deterministic precedence file > env), and secret material is never logged or returned by APIs (no-leak).

## Epic 4: Core S3 File Experience (Browse → Upload → Preview → Download)

End users can browse workspaces, create folders, upload/download files, and preview supported files on S3-backed storage; operators can configure upload chunk/part sizing per backend and per mount where applicable.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 3.4

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/gates.md`

### Completion Notes List

- External API routes are disabled by default (no routes unless enabled).
- Missing/invalid bearer token yields clean `401` with generic details (no-leak).
- Non-allowlisted audiences yield deterministic `403`.
- `OIDC_RS_CLIENT_SECRET` uses refs-only configuration (file/env ref precedence).

### File List

- `docs/resource_server.md`
- `env.d/development/common`
- `src/backend/drive/settings.py`
- `src/backend/core/urls.py`
- `src/backend/core/external_api/authentication.py`
- `src/backend/core/external_api/viewsets.py`
- `src/backend/core/external_api/permissions.py`
- `src/backend/core/utils/secret_refs.py`
- `src/backend/core/tests/conftest.py`
- `src/backend/core/tests/external_api/items/test_external_api_items.py`
- `_bmad-output/implementation-artifacts/latest.txt`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/report.md`
- `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/gates.md`
- `_bmad-output/implementation-artifacts/runs/20260211-124250-3.4/files-changed.txt`
