# Story 7.3: Browse mount paths with deterministic ordering/pagination and virtual entry identifiers

Status: done

## Story

As an end user,
I want to browse a mount path and see file/folder metadata with deterministic ordering and pagination,
So that mount navigation is predictable and scalable.

## Acceptance Criteria

**Given** a mount is enabled and the user has access
**When** the user requests the children of a mount path
**Then** the API returns a deterministic ordering and contract-level pagination/limits.
**And** each returned entry is identified as a virtual entry by `(mount_id, normalized_path)` with deterministic path normalization.

**Given** the Explorer must be capability-driven
**When** listing mount children
**Then** the list response includes the user-relevant per-entry abilities/capabilities required to render actions without dead buttons (as applicable), consistent with Epic 4 patterns for `abilities`.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 7.3

## Dev Agent Record

### Agent Model Used
GPT-5.2 (Codex CLI)


### Debug Log References
- `_bmad-output/implementation-artifacts/runs/20260212-133104-7.3/`


### Completion Notes List
- Added `GET /api/v1.0/mounts/{mount_id}/browse/` with deterministic ordering and
  limit/offset pagination (`limit`, `offset`).
- Introduced deterministic mount path normalization and a static MountProvider
  for contract tests/demos.
- Added backend tests covering ordering, pagination, invalid paths, and 404s for
  missing paths.


### File List
- `src/backend/core/api/viewsets.py`
- `src/backend/core/api/serializers_mounts.py`
- `src/backend/core/mounts/__init__.py`
- `src/backend/core/mounts/paths.py`
- `src/backend/core/mounts/providers/__init__.py`
- `src/backend/core/mounts/providers/base.py`
- `src/backend/core/mounts/providers/static.py`
- `src/backend/core/mounts/registry.py`
- `src/backend/core/tests/mounts/test_api_mounts_browse.py`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260212-133104-7.3/`
