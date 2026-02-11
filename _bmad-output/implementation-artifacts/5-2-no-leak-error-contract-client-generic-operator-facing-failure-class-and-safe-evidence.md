# Story 5.2: No-leak error contract (client-generic) + operator-facing `failure_class` and safe evidence

Status: review

## Story

As an end user and operator,
I want a consistent no-leak error response and messaging contract where client-facing errors remain generic, while operator-facing surfaces provide actionable identifiers and safe evidence,
So that failures are diagnosable without exposing secrets, internal URLs, object keys, or paths.

## Acceptance Criteria

**Given** any request fails on a user-facing surface (API/UI/public share link/media/preview/WOPI/external API)
**When** an error response is returned to the client
**Then** it is clean and no-leak: no stack traces, no raw exceptions, no credentials, no internal URLs, no raw S3 object keys, and no raw mount paths/SMB details.
**And** error detail remains generic for clients (avoid revealing why a token/permission check failed).

**Given** a public MountProvider share link is opened
**When** the token is invalid (`404`) or valid but the target is missing (`410`)
**Then** the client response remains generic and no-leak (no path, no SMB info, no hints beyond the intended 404/410 semantics).
**And** operator-facing surfaces may show `failure_class` + allow-listed safe evidence + `next_action_hint` (no-leak).

**Given** the external API is enabled
**When** a caller is missing/has an invalid token (`401`) or is not allowlisted (`403`)
**Then** the client response remains generic and no-leak (no claim/audience details, no introspection reasoning).
**And** operator-facing diagnostics/artifacts provide `failure_class` + `next_action_hint` + allow-listed safe evidence (no-leak).

**Given** the same failure is observable via operator-facing surfaces (Diagnostics right panel, deterministic artifacts, or logs designed for no-leak)
**When** the operator inspects the failure
**Then** the system provides `failure_class` and `next_action_hint` plus allow-listed safe evidence only (e.g., status codes, request_id, hashes, audience codes), and never relies on “redact after the fact”.

**Given** error messaging is shown in the UI
**When** a capability is unavailable or a prerequisite is missing
**Then** the UI shows an explicit non-leaky “why” and “next action” state (no dead actions), and uses the operator-facing diagnostics as the place to get actionable technical detail.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 5.2

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-145051-5.2/run-report.md`

### Completion Notes List

- No-leak: hash S3 object keys before logging (`file_key_hash`).
- No-leak: sanitize malware detection logs + stored `error_info` allow-list.
- S3 gateway compatibility: fallback for metadata update when `CopyObject` fails.
- Gates: `backend.lint` PASS, `backend.tests` PASS.

### File List

- `src/backend/core/utils/no_leak.py`
- `src/backend/core/api/viewsets.py`
- `src/backend/core/tasks/item.py`
- `src/backend/core/malware_detection.py`
- `src/backend/core/ct_s3/safe.py`
- `src/backend/core/tests/test_malware_detection.py`
- `src/backend/core/tests/items/test_api_item_upload_ended.py`
- `src/backend/core/tests/items/test_api_items_children_create.py`
- `src/backend/core/tests/items/test_api_items_create.py`
- `src/backend/core/tests/tasks/items/test_process_deletion.py`
- `_bmad-output/implementation-artifacts/runs/20260211-145051-5.2/report.md`
