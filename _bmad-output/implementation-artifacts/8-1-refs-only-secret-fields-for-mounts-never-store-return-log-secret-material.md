# Story 8.1: Refs-only secret fields for mounts (never store/return/log secret material)

Status: done

## Story

As an operator,
I want mount credentials to be expressed only as secret references (env var name and/or file path),
So that secret values are never stored in the database, returned by APIs, or leaked into logs/artifacts.

## Acceptance Criteria

**Given** a mount requires credentials
**When** the operator configures the mount
**Then** the configuration stores only references (e.g., `password_secret_ref` and/or `password_secret_path`), never secret values.
**And** secret references are not exposed on end-user APIs; they are provided only via operator-managed configuration (env/files) in v1 (no in-app admin UI in this project).

**Given** any mount-related API response, log line, or deterministic artifact is produced
**When** it includes mount configuration context
**Then** it never includes secret values and avoids leaking sensitive file paths; errors remain no-leak and generic for client-facing surfaces.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 8.1

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-091451-8.1/commands.log`

### Completion Notes List
- Added refs-only validation for mount secret fields in `config_preflight`.
- Ensured preflight output remains no-leak (no secret values or file paths echoed).
- Verified: `make lint`, `make test-back` (PASS).

### File List
- `src/backend/core/management/commands/config_preflight.py`
- `src/backend/core/tests/commands/test_config_preflight.py`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-091451-8.1/report.md`
- `_bmad-output/implementation-artifacts/runs/20260212-091451-8.1/gates.md`
- `_bmad-output/implementation-artifacts/runs/20260212-091451-8.1/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260212-091451-8.1/files-changed.txt`
