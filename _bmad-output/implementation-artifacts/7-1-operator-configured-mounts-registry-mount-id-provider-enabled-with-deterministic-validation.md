# Story 7.1: Operator-configured mounts registry (mount_id, provider, enabled) with deterministic validation

Status: ready-for-dev

## Story

As an operator,
I want to configure mounts with a stable `mount_id`, display name, provider type, and provider-specific non-secret parameters,
So that mounts can be managed without changing S3-backed behavior.

## Acceptance Criteria

**Given** the operator provides mount configuration inputs (settings/env/file-backed configuration)
**When** configuration validation runs
**Then** each mount has a stable, unique `mount_id`, a display name, a provider type, and provider-specific non-secret parameters.
**And** invalid configuration fails early with deterministic `failure_class` + `next_action_hint`, without leaking secrets or internal paths.

**Given** a mount is disabled
**When** users browse/discover mounts
**Then** the disabled mount is not available for end-user actions, and any attempted access yields deterministic, no-leak behavior.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.1

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-085429-7.1/commands.log`

### Completion Notes List
- Added mounts registry parsing/validation from env or file (deterministic, no-leak).
- Added enabled-only mounts discovery API (`/api/v1.0/mounts/`).
- Verified: `make lint`, `make test-back` (PASS).

### File List
- `src/backend/core/services/mounts_registry.py`
- `src/backend/drive/settings.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/urls.py`
- `src/backend/core/tests/mounts/test_api_mounts.py`
- `src/backend/core/tests/test_mounts_registry.py`
- `docs/env.md`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-085429-7.1/report.md`
- `_bmad-output/implementation-artifacts/runs/20260212-085429-7.1/gates.md`
- `_bmad-output/implementation-artifacts/runs/20260212-085429-7.1/commands.log`
- `_bmad-output/implementation-artifacts/runs/20260212-085429-7.1/files-changed.txt`
