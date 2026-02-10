# Axe Storage — MountProvider + SMB v1 (Epics & Stories Draft)

## Goal

Add a **plugin-like MountProvider framework** to Drive so we can implement a **SMB mount v1** (and future mounts) without refactoring the existing S3-first Drive core.

## Non-goals (for this axis)

- No upstream repo interaction by agents.
- No synchronization between SMB and S3.
- No per-path RBAC inside SMB (global mount permissions only).

## Key Definitions

- **Provider**: backend implementation for a protocol (SMB, future WebDAV, etc.).
- **Mount**: an instance of a provider (mount_id + config + credentials in secrets).
- **Virtual entry**: a file/folder in a mount, identified by `(mount_id, path)`.
- **Capabilities**: per-provider feature flags used to enable/disable UI/actions.
- **Audience** (for later contract tests): not S3-specific here, but we keep the mindset of explicit “who calls what” (browser vs backend).

## Cross-cutting Constraints (must hold)

- Repo scope: `Apoze/drive` only.
- No-leak: never log SMB credentials or raw sensitive paths in reports; use hashes for evidence when needed.
- Small PRs: prefer incremental PR-friendly steps (no mega changes).

## Gates (IDs, resolved by gates-runner)

Baseline gates for most stories:

- `backend.lint`
- `backend.tests`

Conditionals (examples; PM will finalize later):

- UI-affecting stories add: `frontend.lint`, `frontend.unit`, `e2e.chrome`
- Storage/mount stories add: `s3.contracts.seaweedfs` **only** if they touch S3/auth/proxy (Mount work should avoid this unless needed)

---

# EPIC STOR-EPIC-01 — MountProvider framework + routing (no behavior change S3)

## Outcome

- A stable **MountProvider interface** and **MountService** to list configured mounts.
- New API surface for mounts that does **not** change existing Item/S3 behavior.

### STOR-01 — Define MountProvider interface + capabilities contract

**Description**

Define a minimal provider interface to support v1 SMB requirements, plus a capability map to keep features explicit.

**Acceptance Criteria**

- Provider interface supports: `list`, `stat`, `open_read`, `open_write`, `mkdir`, `delete`, `move`, `supports_range` (capability), `supports_wopi` (capability), `supports_share_links` (capability).
- Capability keys are stable and documented (no implicit behavior).
- No existing S3 code paths are modified.

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Unit tests for capability defaults and interface validation.

### STOR-02 — Mount definitions: config schema (settings/env) + secret handling

**Description**

Define how mounts are configured in selfhost (static config v1), keeping credentials in secrets.

**Acceptance Criteria**

- Mounts can be declared with stable `mount_id`, provider type, display name, and connection details.
- Credentials are read from secrets/env (not committed, not echoed in logs).
- `mount_id` is stable and validated (no whitespace, unique).

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Unit tests for config parsing/validation (invalid mount_id, missing required fields).

### STOR-03 — MountService + API to list mounts and capabilities

**Description**

Expose mounts to the frontend as a first-class concept (separate from Items).

**Acceptance Criteria**

- New API endpoint returns mounts list: `mount_id`, `display_name`, `provider`, `capabilities`, and a minimal “root path”.
- Response contains no secrets.
- Existing Items endpoints unchanged.

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- API tests verifying no secrets and stable schema.

### STOR-04 — Frontend entry point for mounts (navigation only)

**Description**

Add a UI entry point to display mounts, without implementing SMB operations yet.

**Acceptance Criteria**

- UI shows configured mounts (name + type).
- No changes to existing Drive S3 UI flows.

**Gates**

- required: `frontend.lint`, `frontend.unit`
- conditional: add `e2e.chrome` when stable selectors are available

**Test Checklist**

- Frontend unit test for mounts listing view.

---

# EPIC STOR-EPIC-02 — SMB provider v1 (basic list/read)

## Outcome

- A SMB provider implementing list/stat/read streams.
- Basic browsing and download through Drive backend (gateway model).

### STOR-05 — Implement SMBProvider list/stat/read (streaming)

**Description**

Implement SMB provider with timeouts and safe error mapping.

**Acceptance Criteria**

- Can list directories and stat entries.
- Can stream-download a file through backend without loading full file in memory.
- Timeouts/concurrency limits are configurable.
- Errors are mapped to stable classes (not raw stack traces).

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Unit tests for error mapping and path normalization.

### STOR-06 — Backend API: browse mount path + download file

**Description**

Create API endpoints to browse a mount and to download a file (auth required in v1 unless share link is used later).

**Acceptance Criteria**

- List endpoint supports pagination (or at least limit/offset) and deterministic ordering.
- Download endpoint supports streaming and emits correct content headers.
- No-leak: logs do not include raw SMB paths by default.

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Integration tests with a Samba container (compose) for list + download.

### STOR-07 — Frontend: browse mount + download action

**Acceptance Criteria**

- UI can browse directories and download files.
- Capability-driven UI: hide/disable actions not supported by the provider.

**Gates**

- required: `frontend.lint`, `frontend.unit`
- conditional: `e2e.chrome` (browse + download smoke)

**Test Checklist**

- E2E smoke: open mounts view → browse folder → download file (artifact on failure).

---

# EPIC STOR-EPIC-03 — SMB upload + preview (v1 requirements)

## Outcome

- Upload to SMB via backend gateway (no presign).
- Preview pipeline works with explicit fallbacks and clear limits.

### STOR-08 — SMB upload: streaming write + atomic finalize (temp + rename)

**Description**

Browser → backend → SMB streaming upload, large-file safe.

**Acceptance Criteria**

- Upload uses streaming; no full buffering in memory.
- Writes to a temp path then renames to final name (best-effort atomic).
- Clear error messages (timeouts, permission denied, insufficient space).
- Limits: max concurrency and max upload size are configurable.

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Integration test: upload file to SMB mount and verify it exists and is readable.

### STOR-09 — SMB preview: range support when available, explicit fallback when not

**Acceptance Criteria**

- If provider supports range reads, preview uses range.
- If not, preview is either disabled (with UI warning) or uses a documented fallback with hard limits.
- Capability-driven UI warnings (no surprises).

**Gates**

- required: `backend.lint`, `backend.tests`, `frontend.lint`, `frontend.unit`

**Test Checklist**

- E2E: preview a small file; ensure clear behavior for unsupported preview.

---

# EPIC STOR-EPIC-04 — SMB share links + WOPI (capability-driven)

## Outcome

- Share links for `(mount_id, path)` (accepted to break if path changes outside Drive).
- WOPI for SMB without requiring S3 bucket versioning (per-backend rule).

### STOR-10 — Share links for mounts: token model + enforcement

**Description**

Create share links tied to mount_id + path. Drive enforces access via token.

**Acceptance Criteria**

- Share link token maps to `(mount_id, path)` and reach (`public`/`authenticated`/`restricted`) as per Drive conventions.
- If SMB path changed/deleted outside Drive, link returns a clean 404/410 (accepted behavior).
- No per-path SMB RBAC: access is global per mount + share token rules in Drive.

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Unit tests for token enforcement and “path missing” behavior.

### STOR-11 — WOPI for SMB: version string + locks + save pipeline

**Description**

Implement WOPI operations for mount files.

**Acceptance Criteria**

- WOPI enablement is per-backend capability:
  - S3 requires bucket versioning (existing rule)
  - SMB uses an application version string (e.g. `mtime+size`) + locks
- Locks are robust (TTL + release) and do not leak secrets/paths.
- Save writes back to SMB via backend gateway.

**Gates**

- required: `backend.lint`, `backend.tests`

**Test Checklist**

- Integration tests for WOPI endpoints (token issuance, GetFile, PutFile stub with mock Collabora).

### STOR-12 — UI: capability-driven share/WOPI actions for mounts

**Acceptance Criteria**

- UI shows share/WOPI actions only when `capabilities` enable them.
- Clear warnings if disabled (no silent failures).

**Gates**

- required: `frontend.lint`, `frontend.unit`
- conditional: `e2e.chrome` for share link open flow (minimal)

**Test Checklist**

- E2E: create share link for SMB file → open link → download/preview.

---

## Notes for PM/QA handoff

- This document is a Phase-3 (Idea Development) draft. PM should translate each story into the BMAD registry format (IDs, AC, gates IDs, test_checklist).
- SMB integration tests should rely on a containerized Samba service in the dev stack to keep runs deterministic.
- Consider adding a dedicated failure_class set for mount operations (mirrors the S3/E2E/gates vocabulary).
