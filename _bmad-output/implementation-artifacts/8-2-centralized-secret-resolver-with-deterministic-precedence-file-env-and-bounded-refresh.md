# Story 8.2: Centralized secret resolver with deterministic precedence (file > env) and bounded refresh

Status: ready-for-dev

## Story

As an operator,
I want a centralized, provider-agnostic secret resolver with deterministic precedence and bounded refresh,
So that providers can fetch secrets consistently without restarts and without duplicating resolver logic.

## Acceptance Criteria

**Given** both `password_secret_path` and `password_secret_ref` are configured
**When** a provider requests the secret value at runtime
**Then** resolution precedence is deterministic and documented: file path > env ref.

**Given** the resolver caches secret values for performance
**When** the configured refresh interval elapses or the resolver detects a change (implementation-defined)
**Then** subsequent operations observe updated secret values within a bounded, operator-configurable time.

**Given** secret resolution fails (missing file/env, permission denied, malformed)
**When** the failure is returned to clients
**Then** client-facing errors remain generic/no-leak, and operator-facing surfaces provide `failure_class` + `next_action_hint` plus allow-listed safe evidence only.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 8.2

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


