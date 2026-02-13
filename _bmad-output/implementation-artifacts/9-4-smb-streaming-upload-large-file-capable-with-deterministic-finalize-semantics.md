# Story 9.4: SMB streaming upload (large-file capable) with deterministic finalize semantics

Status: done

## Story

As an end user,
I want to upload files to an SMB-backed mount via backend-mediated streaming with deterministic finalize behavior,
So that large uploads succeed reliably without creating “ghost” entries on failure.

## Acceptance Criteria

**Given** I upload a file to an SMB-backed mount
**When** the backend processes the upload
**Then** it streams the upload (no full buffering) and applies documented limits/timeouts/concurrency controls.

**Given** an upload uses a temp/intermediate target (implementation-defined)
**When** the upload completes successfully
**Then** finalize semantics are deterministic (e.g., temp → final rename best-effort) and the resulting entry is visible in browse.

**Given** the upload fails or is interrupted
**When** the user refreshes or retries
**Then** the system behaves deterministically per Epic 5.3 (no implicit ghost “ready” entries; actionable failure state; idempotent retry semantics where applicable).

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 9.4

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- Run: `_bmad-output/implementation-artifacts/runs/20260212-165526-9.4/`
- Gates report: `_bmad-output/implementation-artifacts/runs/20260212-165526-9.4/run-report.md`
- Commands: `_bmad-output/implementation-artifacts/runs/20260212-165526-9.4/commands.log`

### Completion Notes List
- Implemented streaming mount uploads for SMB provider (multipart, no full buffering).
- Temp → final best-effort rename finalize semantics; best-effort temp cleanup on failure.
- Added size/time/concurrency limits and documented them in `docs/env.md`.
- Added backend tests covering success, existing target, and size limit behavior.

### File List
- `src/backend/core/api/viewsets.py`
- `src/backend/core/mounts/providers/smb.py`
- `src/backend/core/tests/mounts/test_api_mounts_upload_streaming.py`
- `src/backend/drive/settings.py`
- `docs/env.md`
- `_bmad-output/implementation-artifacts/9-4-smb-streaming-upload-large-file-capable-with-deterministic-finalize-semantics.md`
- `_bmad-output/implementation-artifacts/runs/20260212-165526-9.4/`
