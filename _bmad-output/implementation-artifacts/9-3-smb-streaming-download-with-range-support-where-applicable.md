# Story 9.3: SMB streaming download with Range support where applicable

Status: done

## Story

As an end user,
I want to download SMB-backed mount files via backend-mediated streaming (with Range where supported),
So that large downloads work efficiently and reliably.

## Acceptance Criteria

**Given** I download a mount file from an SMB mount
**When** the backend serves the download
**Then** it streams content without buffering the entire file in memory (NFR1).

**Given** the client sends a Range request and the SMB provider supports range reads
**When** the backend serves the response
**Then** it returns a correct partial response (e.g., `206` with appropriate headers) and remains deterministic and no-leak on failures.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 9.3

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- Run: `_bmad-output/implementation-artifacts/runs/20260212-163414-9.3/`
- Gates report: `_bmad-output/implementation-artifacts/runs/20260212-163414-9.3/run-report.md`
- Commands: `_bmad-output/implementation-artifacts/runs/20260212-163414-9.3/commands.log`

### Completion Notes List
- Implemented streaming mount downloads for SMB provider (no full buffering).
- Added single `Range: bytes=...` support when provider supports range reads.
- Added tests for full and partial responses + unsatisfiable ranges.

### File List
- `src/backend/core/api/viewsets.py`
- `src/backend/core/mounts/providers/smb.py`
- `src/backend/core/tests/mounts/test_api_mounts_download_streaming.py`
- `_bmad-output/implementation-artifacts/9-3-smb-streaming-download-with-range-support-where-applicable.md`
- `_bmad-output/implementation-artifacts/runs/20260212-163414-9.3/`
