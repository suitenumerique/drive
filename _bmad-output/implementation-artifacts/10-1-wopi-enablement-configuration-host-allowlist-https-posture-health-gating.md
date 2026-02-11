# Story 10.1: WOPI enablement configuration (host allowlist, HTTPS posture, health gating)

Status: in-progress

## Story

As an operator,
I want to configure WOPI/Collabora integration with strict host allowlisting derived from `DRIVE_PUBLIC_URL` and clear health gating,
So that WOPI is safe-by-default and “enabled & healthy” is explicit and operator-debuggable.

## Acceptance Criteria

**Given** WOPI is enabled by configuration
**When** configuration validation runs
**Then** allowlisted WOPI hosts/origins are derived from `DRIVE_PUBLIC_URL` by default and are validated deterministically (no wildcards, no ambiguous parsing).
**And** production requires HTTPS for WOPI-related public surfaces (dev override only if explicitly enabled, consistent with Epic 1/2 TLS rules).

**Given** WOPI is enabled
**When** operator-facing diagnostics/health checks run
**Then** the system exposes an “enabled & healthy” vs “enabled but unhealthy” vs “disabled” state with `failure_class` + `next_action_hint` and allow-listed safe evidence only (no-leak).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.1

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-233642-10.1/`
- Gates: `_bmad-output/implementation-artifacts/runs/20260211-233642-10.1/run-report.md`
- Commands: `_bmad-output/implementation-artifacts/runs/20260211-233642-10.1/commands.log`

### Completion Notes List

- Defaulted `WOPI_SRC_BASE_URL` to `DRIVE_PUBLIC_URL` when WOPI is enabled.
- Added deterministic `config_preflight` checks for WOPI enablement/discovery URLs.
- Added `python manage.py wopi_health` to expose enabled/healthy status (no-leak).
- Updated WOPI settings tests to set `DRIVE_PUBLIC_URL` when WOPI is enabled.

### File List

- `src/backend/drive/settings.py`
- `src/backend/core/management/commands/config_preflight.py`
- `src/backend/wopi/services/health.py`
- `src/backend/wopi/management/commands/wopi_health.py`
- `src/backend/core/tests/test_settings.py`
- `src/backend/core/tests/commands/test_config_preflight.py`
- `docs/env.md`
- `_bmad-output/implementation-artifacts/runs/20260211-215958-10.1/`
- `_bmad-output/implementation-artifacts/runs/20260211-225555-10.1/`
- `_bmad-output/implementation-artifacts/runs/20260211-233642-10.1/`
