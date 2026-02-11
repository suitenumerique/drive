# Story 4.6: Operator-configurable upload part/chunk sizing (documented defaults + deterministic validation)

Status: ready-for-dev

## Story

As an operator,
I want upload part/chunk sizing for large uploads to be documented with defaults/limits and configurable per backend (and per mount where applicable),
So that large transfers remain reliable and tunable in real self-host environments.

## Acceptance Criteria

**Given** the system runs with S3-backed storage and backend-mediated transfers exist (e.g., WOPI save flows, server-side transfers)
**When** I consult documentation and environment configuration references
**Then** it documents default values and operator-configurable limits for multipart/transfer sizing (e.g., `S3_TRANSFER_CONFIG_MULTIPART_THRESHOLD`, `S3_TRANSFER_CONFIG_MULTIPART_CHUNKSIZE`, and related concurrency settings), including what flows they affect.
**And** it clarifies that these settings primarily affect backend-mediated transfers (e.g., boto3 `TransferConfig` usage) and server-side interactions.
**And** it clarifies that browser presigned PUT uploads are `EXTERNAL_BROWSER` flows and are not affected unless multipart is explicitly implemented in the browser client (otherwise these settings are a no-op for presigned PUT).

**Given** configuration preflight/validation runs
**When** multipart/chunk sizing settings are invalid or unsafe (e.g., non-integers, values outside documented bounds, chunksize > threshold, or incompatible values)
**Then** the system fails early with deterministic `failure_class` + `next_action_hint`, and remains no-leak.
**And** accepted values are validated (type + min/max) and normalized deterministically (e.g., bytes as integers), to avoid “passes validation but fails at runtime” configurations.

**Given** MountProvider uploads are enabled for a mount (future epics)
**When** mount-specific chunk sizing is supported
**Then** configuration is per-mount where applicable and is documented consistently using the same validation/no-leak patterns.

## Epic 5: Resilience & Messaging Patterns (Cross-cutting)

Establish cross-cutting patterns (time-bounded long-running states, actionable errors, no-leak messaging + safe evidence) reused across end-user flows (S3, share links, mounts/SMB, WOPI) and operator-first surfaces (Diagnostics right panel), rather than a UI-only silo.

## Tasks / Subtasks

- [ ] Implement the Acceptance Criteria
- [ ] Add/adjust tests and/or smoke checks as required
- [ ] Update docs/runbooks as required
- [ ] Verification (record results)
- [ ] Traceability run report artifacts

## Dev Notes

- Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.6

## Dev Agent Record

### Agent Model Used


### Debug Log References


### Completion Notes List


### File List


