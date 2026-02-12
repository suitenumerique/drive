# Story 10.3: Reverse-proxy-compatible WOPI launch flow with short-lived tokens

Status: done

## Story

As an end user,
I want to launch WOPI editing for an eligible file through a reverse-proxy-compatible flow,
So that WOPI works in self-host environments without direct internal network access.

## Acceptance Criteria

**Given** WOPI is enabled & healthy and a file is eligible
**When** I launch WOPI editing
**Then** the system issues a short-lived, no-leak WOPI access token and redirects/loads the WOPI client in a way compatible with reverse proxies.
**And** client-facing failures remain generic/no-leak; operator-facing surfaces provide `failure_class` + `next_action_hint`.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 10.3

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- Run folder: `_bmad-output/implementation-artifacts/runs/20260212-001009-10.3/`
- Gates: `_bmad-output/implementation-artifacts/runs/20260212-001009-10.3/run-report.md`
- Commands: `_bmad-output/implementation-artifacts/runs/20260212-001009-10.3/commands.log`

### Completion Notes List

- Built absolute `WOPISrc` using `WOPI_SRC_BASE_URL`, `DRIVE_PUBLIC_URL`, or request base.
- Added an explicit base-url override to the launch URL builder for proxy-aware flows.
- Shortened default `WOPI_ACCESS_TOKEN_TIMEOUT` and updated `docs/env.md`.

### File List

- `src/backend/core/api/viewsets.py`
- `src/backend/wopi/utils/__init__.py`
- `src/backend/core/tests/items/test_api_items_wopi.py`
- `src/backend/drive/settings.py`
- `docs/env.md`
- `_bmad-output/implementation-artifacts/runs/20260211-222743-10.3/`
- `_bmad-output/implementation-artifacts/runs/20260211-230510-10.3/`
- `_bmad-output/implementation-artifacts/runs/20260211-235535-10.3/`
- `_bmad-output/implementation-artifacts/runs/20260212-001009-10.3/`
