# Story 3.3: External API allowlist for resources and actions (strict, no wildcards)

Status: review

## Story

As an operator,
I want to enable the external API surface using a strict allowlist of resources and actions,
So that only explicitly permitted endpoints/actions are exposed (disabled-by-default, no wildcards).

## Acceptance Criteria

**Given** Resource Server mode is enabled
**When** a resource is not enabled in the external API configuration
**Then** its routes are not exposed under `/external_api/v1.0/...` (404).

**Given** a resource is enabled but an action is not allowlisted for that resource
**When** a client attempts the disallowed action
**Then** the request is rejected deterministically with a documented status code (v1: `403`), with a clean no-leak response.

**Given** a resource and action are allowlisted
**When** a client calls the corresponding external API endpoint
**Then** the request is permitted (subject to the normal authorization rules for that resource) and behaves consistently with the internal API contract.

**Given** the operator configures external API allowlists
**When** preflight/validation runs
**Then** configuration is validated deterministically and at action-level (resource + action names, not raw path prefixes), with no ambiguous parsing and no wildcards.
**And** failures include `failure_class` + `next_action_hint` (no-leak).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 3.3

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-122401-3.3/report.md`

### Completion Notes List

- External API resources are now truly enablement-gated (disabled resources 404).
- Added deterministic EXTERNAL_API config validation (strict, no wildcards).

### File List

- `src/backend/core/urls.py`
- `src/backend/drive/settings.py`
- `docs/resource_server.md`
- `docs/failure-class-glossary.md`
- `src/backend/core/tests/conftest.py`
- `src/backend/core/tests/test_settings.py`
- `src/backend/core/tests/external_api/items/test_external_api_items.py`
- `_bmad-output/implementation-artifacts/runs/20260211-122401-3.3/report.md`
