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
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-095311-8.2/`

### Completion Notes List
- Implemented centralized runtime secret resolver with deterministic precedence:
  file path > env ref.
- Added bounded refresh window via `MOUNTS_SECRET_REFRESH_SECONDS` (default 60s).
- Added deterministic, no-leak `SecretResolutionError` with `failure_class` +
  `next_action_hint` and allow-listed safe evidence.
- Added unit tests covering precedence, bounded refresh, and no-leak failures.

### File List
- `src/backend/core/utils/secret_resolver.py`
- `src/backend/core/services/secret_resolver.py`
- `src/backend/core/tests/utils/test_secret_resolver.py`
- `src/backend/drive/settings.py`
- `docs/env.md`
- `docs/failure-class-glossary.md`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-095311-8.2/`
