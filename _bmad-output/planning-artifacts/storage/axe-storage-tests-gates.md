# Axe Storage — Tests & Gates (BMAD v6 Draft)

## Goal

Provide a deterministic **Tests + Gates + DoD** layer for the Storage axis so the dev agent can execute STOR-* stories end-to-end with minimal ambiguity.

This document complements:

- `_bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md`
- `docs/failure-class-glossary.md`

## Definitions

- **Blocking (strict)**: must pass in CI and in agent dev mode.
- **Quick mode (`--quick`)**: may skip explicitly listed non-critical checks, but must record `skipped` in reports.
- **Evidence**: allowed fields in reports (no-leak): status codes, latency buckets, request_id, hashes. No raw SMB paths/keys/credentials.

## Cross-cutting DoD (applies to all STOR-* stories)

- Code style: all code/comments in English.
- Secrets: SMB credentials only from secrets/env, never logged.
- No behavior change to S3 path unless story explicitly targets it.
- Reports: every gate emits `gate_id`, `result`, `failure_class` (if fail), and `next_action_hint`.
- Strict vs quick: any skipped gate must be explicit in report (`result=skipped`).

## Gate IDs (recommended)

Use stable identifiers in the registry; runner resolves them to commands:

- `backend.lint`
- `backend.tests`
- `frontend.lint`
- `frontend.unit`
- `e2e.chrome`
- `mounts.integration.smb` (new, blocking when SMB features touched)
- `mounts.e2e.smb` (new, blocking when UI mount flows touched)

Optional/non-blocking:

- `mounts.perf.smb` (future)

## Strict vs Quick — Skippable Policy (recommended)

**Never skippable (even in quick):**

- `backend.lint`, `backend.tests`
- `frontend.lint`, `frontend.unit` (when frontend touched)
- `mounts.integration.smb` (when mount backend touched)

**Skippable in quick (must be recorded as skipped):**

- `mounts.e2e.smb` (if offline / chrome unavailable; CI remains strict)
- `e2e.chrome` (only if story is backend-only and no UI regression risk)

Rationale: quick mode must not become “skip everything”.

---

# Test Infrastructure: Samba integration environment (deterministic)

## Principle

Integration tests must run against a deterministic SMB endpoint to avoid external dependencies.

## Recommended setup (conceptual)

- Add a Samba service to the dev stack (compose), with:
  - a dedicated share for tests (e.g. `/share`)
  - a single service account (global permissions)
  - predictable test dataset seeded on startup

## Test data strategy

- For each test run, create a unique root folder for isolation:
  - `/share/test-runs/<run-id>/...`
- Do not log raw test paths; log hash or run-id only.

## Failure classes for the environment (examples)

- `mount.smb.env.unreachable`
- `mount.smb.env.auth_failed`
- `mount.smb.env.share_not_found`

---

# Story-by-story Tests & Gates

> Format:
> - **Blocking gates (strict)**
> - **Quick mode behavior**
> - **Test checklist**
> - **DoD notes**

## STOR-01 — MountProvider interface + capabilities contract

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`

**Quick mode**

- same as strict

**Test checklist**

- Unit: capability defaults and validation (no implicit behavior)
- Unit: interface input validation (mount_id normalization, path normalization rules)

**DoD notes**

- No S3 path changes.

## STOR-02 — Mount config schema + secret handling

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`

**Test checklist**

- Unit: config parsing rejects missing required fields
- Unit: mount_id uniqueness and format validation
- Unit: “no secret in logs” (ensure config rendering/redaction)

## STOR-03 — MountService + API list mounts/capabilities

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`

**Test checklist**

- API: mounts list returns expected schema and no secrets
- API: capabilities are stable keys (snapshot test)

## STOR-04 — Frontend mounts navigation (read-only)

**Blocking gates (strict)**

- `frontend.lint`
- `frontend.unit`

**Quick mode**

- E2E may be skipped; unit/lint remain required

**Test checklist**

- Frontend unit: mounts list view renders
- (Optional strict) `e2e.chrome`: open mounts page

## STOR-05 — SMBProvider list/stat/read (streaming)

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`
- `mounts.integration.smb`

**Quick mode**

- `mounts.integration.smb` remains required (backend contract)

**Test checklist**

- Unit: error mapping (timeout → stable exception class)
- Integration: list + stat + streaming read against Samba container
- No-leak: logs must not contain credentials or raw paths

## STOR-06 — Backend API browse/download for mounts

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`
- `mounts.integration.smb`

**Test checklist**

- Integration: browse endpoint (pagination/limit) deterministic ordering
- Integration: download endpoint streams content
- Negative: missing path returns clean error (404/410 equivalent), not stack trace

## STOR-07 — Frontend browse/download for mounts

**Blocking gates (strict)**

- `frontend.lint`
- `frontend.unit`
- `mounts.e2e.smb` (recommended)

**Quick mode**

- `mounts.e2e.smb` may be skipped if offline; must record skipped.

**Test checklist**

- E2E: open mount → browse folder → download file (artifacts on fail)
- UI: capability-driven action visibility

## STOR-08 — SMB upload streaming + atomic finalize

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`
- `mounts.integration.smb`

**Test checklist**

- Integration: upload a large-enough file (streaming) and verify readability
- Integration: atomic finalize semantics (temp → rename), best-effort
- Negative: timeout → clean error, no partial “final” file

## STOR-09 — SMB preview (range when available, fallback otherwise)

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`
- `frontend.lint`
- `frontend.unit`
- `mounts.integration.smb`
- `mounts.e2e.smb` (recommended)

**Quick mode**

- may skip `mounts.e2e.smb` if offline; must record.

**Test checklist**

- Integration: preview endpoint for small text/image (if supported)
- UI: clear warning when preview disabled/limited

## STOR-10 — Share links for mounts: token model + enforcement

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`
- `mounts.integration.smb`

**Test checklist**

- Unit: token maps to `(mount_id, path)` and reach
- Integration: shared link works for existing path
- Integration: if path changed/missing, returns clean 404/410 behavior

## STOR-11 — WOPI for SMB: version string + locks + save pipeline

**Blocking gates (strict)**

- `backend.lint`
- `backend.tests`
- `mounts.integration.smb`

**Test checklist**

- Unit: version string generation (mtime+size) stable
- Unit: lock acquisition/release with TTL
- Integration: PutFile writes back to SMB through backend gateway (mock Collabora)

## STOR-12 — UI: capability-driven share/WOPI actions for mounts

**Blocking gates (strict)**

- `frontend.lint`
- `frontend.unit`
- `mounts.e2e.smb` (recommended)

**Test checklist**

- E2E: create share link for SMB file → open link → download/preview
- UI: action visibility follows capabilities (no dead buttons)

---

# Mount failure_class glossary (recommended additions)

Use the same canonical format as other domains: `mount.<provider>.<category>.<reason>`.

## SMB environment / auth

- `mount.smb.env.unreachable`
- `mount.smb.env.auth_failed`
- `mount.smb.env.share_not_found`

## SMB operations

- `mount.smb.list_failed`
- `mount.smb.stat_failed`
- `mount.smb.read_failed`
- `mount.smb.write_failed`
- `mount.smb.upload_timeout`
- `mount.smb.atomic_rename_failed`
- `mount.smb.range_unsupported`

## Drive integration around mounts

- `mount.drive.capability_mismatch` (UI/action requested but capability false)
- `mount.drive.share_token_invalid`
- `mount.drive.wopi_lock_conflict`
- `mount.drive.wopi_save_failed`

## UI/E2E around mounts

- `mount.ui.navigation_failed`
- `mount.ui.download_failed`
- `mount.ui.preview_failed`
