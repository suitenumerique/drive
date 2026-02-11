# Story 3.1: BYO OIDC authentication (refs-only secrets, config validation, smoke login proof)

Status: ready-for-dev

## Story

As an operator,
I want Drive to support authentication via an operator-provided external OIDC Identity Provider with deterministic configuration validation and a smoke login flow,
So that the deployment is self-host reliable (no surprises) without coupling v1 to a specific IdP.

## Acceptance Criteria

**Given** the operator provides OIDC configuration inputs (issuer/discovery URL, client id, client secret ref via env var name and/or file path with deterministic precedence (file > env), and redirect/origin allowlists as defined in Epic 1 Story 1.2)
**When** configuration preflight/validation runs
**Then** it validates these inputs deterministically (no ambiguous parsing; no wildcards; production requires HTTPS unless the same centralized dev-only override used by Epic 1/2 TLS rules is explicitly enabled).
**And** secret material is never returned by APIs and is never logged (no-leak).
**And** failures return deterministic `failure_class` + `next_action_hint` (no-leak).

**Given** `DRIVE_PUBLIC_URL` is set
**When** redirect URIs are computed/validated
**Then** the default allowed redirect URIs match the canonical host derived from `DRIVE_PUBLIC_URL`.
**And** any additional redirect URIs require explicit configuration via the dedicated allowlist (Epic 1 Story 1.2), with deterministic validation and no wildcards.

**Given** production is configured with an operator-provided external OIDC IdP
**When** a user performs the login flow
**Then** authentication succeeds end-to-end and the user can prove session validity by fetching a minimal authenticated endpoint (e.g., `/api/v1.0/users/me/`) and/or browsing a workspace.

**Given** a dev fixture IdP is used
**When** documentation mentions Keycloak
**Then** it is explicitly described as dev/reference fixture only (BYO IdP remains the production posture).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 3.1

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


