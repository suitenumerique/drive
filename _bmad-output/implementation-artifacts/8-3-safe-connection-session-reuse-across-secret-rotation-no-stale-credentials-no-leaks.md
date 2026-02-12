# Story 8.3: Safe connection/session reuse across secret rotation (no stale credentials, no leaks)

Status: done

## Story

As an operator,
I want secret rotation to be safe with connection/session reuse,
So that stale credentials are not reused after rotation and failures do not leak sensitive material.

## Acceptance Criteria

**Given** a secret value changes (rotation)
**When** new mount operations begin after the bounded refresh window
**Then** new connections/sessions use the updated credentials.

**Given** a connection/session is pooled or reused
**When** the resolver indicates credentials have changed
**Then** reuse is safe: stale sessions are not used for new operations (or are deterministically re-authenticated) and failures remain no-leak.

## Epic 9: SMB Mount v1 Provider: Streaming Upload/Download/Preview (Implementation-level)

Provider epic (implementation-level): SMB-specific configuration + backend-mediated streaming download/upload and preview where supported, implemented on top of the Epic 7 framework contracts; share links are handled via Epics 6 (S3) and 7 (MountProvider), and WOPI via Epic 10.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 8.3

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)

### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-100020-8.3/`

### Completion Notes List
- Implemented a version-bound pooled resource wrapper to prevent stale
  connection/session reuse after credential rotation is observed.
- Wrapped factory failures deterministically and no-leak (no credentials in
  error messages).
- Added unit tests covering reuse, rotation, and no-leak wrapping.

### File List
- `src/backend/core/utils/rotating_resource.py`
- `src/backend/core/tests/utils/test_rotating_resource.py`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-100020-8.3/`
