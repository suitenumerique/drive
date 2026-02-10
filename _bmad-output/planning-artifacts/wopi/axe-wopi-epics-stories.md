# Axe WOPI / Collabora — Epics & Stories Draft (BMAD v6)

## Goal

Provide a WOPI integration that works for:

- S3-backed files (requires bucket versioning)
- SMB-backed mount files (does **not** require S3 versioning; uses app version string + locks)

WOPI must be capability-driven and safe-by-default.

## Non-goals

- No full “Collabora E2E automation” required for v1 (provide deterministic manual runbook + integration tests).
- No upstream repo interaction by agents.

## Cross-cutting constraints (must hold)

- `DRIVE_PUBLIC_URL` is the canonical host allowlist input.
- Tokens have short TTL; locks have TTL and safe release.
- Capabilities determine whether WOPI actions are available (S3 vs SMB).

---

# EPIC WOPI-EPIC-01 — Capability-driven enablement (per backend)

## Outcome

- WOPI is enabled/disabled per backend based on explicit capabilities and prerequisites.

### WOPI-01 — Capability model for WOPI per backend

**Acceptance Criteria**

- S3 backend advertises WOPI capability only when versioning is available.
- SMB backend advertises WOPI capability when version string + locks are implemented.
- UI uses capabilities to show/hide WOPI actions (no dead buttons).

**Gates**

- `backend.lint`, `backend.tests`, `frontend.lint`, `frontend.unit`

---

# EPIC WOPI-EPIC-02 — S3 WOPI prerequisite: bucket versioning validation

## Outcome

- Drive can detect/validate S3 bucket versioning prerequisite for WOPI.

### WOPI-02 — S3 versioning check + clear operator feedback

**Acceptance Criteria**

- If S3 versioning is required but not enabled:
  - WOPI is disabled for S3 files
  - UI/API provides a clear operator-facing message (no vague failures)

**Gates**

- `backend.lint`, `backend.tests`

---

# EPIC WOPI-EPIC-03 — SMB WOPI: version string + locks + save pipeline

## Outcome

- WOPI works for SMB mounts using an application-level version string (e.g. `mtime+size`) and lock manager.

### WOPI-03 — SMB file version string (mtime+size)

**Acceptance Criteria**

- Version string changes whenever file content changes.
- Version computation is deterministic and safe (no path leak).

**Gates**

- `backend.lint`, `backend.tests`, `mounts.integration.smb`

### WOPI-04 — Lock manager (TTL + release + conflict handling)

**Acceptance Criteria**

- Locks have TTL; conflicts return deterministic error.
- Locks can be released; stale locks expire.

**Gates**

- `backend.lint`, `backend.tests`

### WOPI-05 — Save pipeline: PutFile writes back to SMB via backend gateway

**Acceptance Criteria**

- PutFile writes to SMB safely (streaming, atomic finalize best-effort).
- Errors are mapped to stable failure classes.

**Gates**

- `backend.lint`, `backend.tests`, `mounts.integration.smb`

---

# EPIC WOPI-EPIC-04 — Security: allowlists, TLS, TTLs

## Outcome

- WOPI endpoints enforce host allowlist and operate safely in prod.

### WOPI-06 — Host allowlist based on `DRIVE_PUBLIC_URL`

**Acceptance Criteria**

- WOPI launch URLs and callbacks are consistent with `DRIVE_PUBLIC_URL`.
- In prod, HTTPS is required.

**Gates**

- `backend.lint`, `backend.tests`

### WOPI-07 — Token TTL policy (short, documented)

**Acceptance Criteria**

- Token TTL is short (minutes) and documented.
- Token refresh strategy is explicit (if needed).

**Gates**

- `backend.lint`, `backend.tests`

---

# EPIC WOPI-EPIC-05 — Testing strategy & runbook

## Outcome

- Deterministic integration tests cover WOPI endpoints.
- A manual runbook exists for full Collabora end-to-end validation.

### WOPI-08 — Integration tests for WOPI endpoints (mock Collabora)

**Acceptance Criteria**

- Tests cover token issuance, GetFile, PutFile (S3 and SMB paths as applicable).
- No reliance on external Collabora server in CI.

**Gates**

- `backend.lint`, `backend.tests`

### WOPI-09 — Manual E2E runbook (reproducible)

**Acceptance Criteria**

- Runbook describes:
  - how to bring up Collabora + Drive in dev
  - which file types to test
  - expected outcomes and troubleshooting

**Gates**

- `backend.lint`, `backend.tests`

---

## Notes for PM/QA handoff

- PM should map WOPI stories to the Storage axis stories (SMB upload/atomic finalize is a prerequisite).
- QA should define explicit failure classes for WOPI flows aligned with the global glossary.
