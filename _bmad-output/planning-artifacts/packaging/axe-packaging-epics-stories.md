# Axe Packaging (Self-host) — Epics & Stories Draft (BMAD v6)

## Goal

Provide a **production-grade self-host packaging** baseline for `Apoze/drive`:

- Docker (single machine) baseline with **Nginx edge**
- Kubernetes support (Ingress + cert-manager) as a documented path
- A single canonical external URL (`DRIVE_PUBLIC_URL`)
- Deterministic upgrade/rollback and backup/restore runbooks

## Non-goals

- No dependency on Traefik; Traefik is documentation/variant only.
- No mixed TLS modes (no “half TLS”).
- No upstream repo interaction by agents.

## Cross-cutting constraints (must hold)

- `DRIVE_PUBLIC_URL` is the canonical base URL for redirects, WOPI allowlist, public links, CORS.
- Explicit separation INTERNAL/PROXY vs EXTERNAL/BROWSER for object storage endpoints (validated by S3 CTs).
- Secrets are never committed and never logged.

---

# EPIC PKG-EPIC-01 — Canonical URL + configuration model

## Outcome

- One canonical public URL (`DRIVE_PUBLIC_URL`) and documented derivations.
- A validated config model that fails early when inconsistent.

### PKG-01 — Define `DRIVE_PUBLIC_URL` and derivation rules

**Acceptance Criteria**

- `DRIVE_PUBLIC_URL` exists and is used as the single source of truth for:
  - OIDC redirect URLs
  - WOPI host allowlist
  - share link base URL
  - CORS/public endpoints as needed
- Document “how to compute” derived URLs (no duplication).

**Gates**

- `backend.lint`, `backend.tests`

### PKG-02 — Config validation + preflight failures (secrets + URLs)

**Acceptance Criteria**

- Preflight fails with deterministic `failure_class` when:
  - `DRIVE_PUBLIC_URL` missing/invalid
  - required secrets missing (DB, S3, OIDC, SMTP optional)
  - INTERNAL/EXTERNAL storage endpoints inconsistent
- No secrets appear in logs/reports.

**Gates**

- `backend.lint`, `backend.tests`

---

# EPIC PKG-EPIC-02 — Nginx edge baseline (Docker)

## Outcome

- Nginx is the baseline edge proxy for Docker deployments.
- Contractual media flow is preserved (`auth_request` → SigV4 headers).

### PKG-03 — Nginx edge templates (dev + prod) aligned

**Acceptance Criteria**

- Nginx templates cover:
  - `/media` auth_request flow (media-auth) + SigV4 header propagation (incl. optional STS token)
  - `/media/preview`
  - OIDC endpoints proxying (Keycloak in dev)
- Dev and prod templates stay aligned in contract behavior.

**Gates**

- `backend.lint`, `backend.tests`

### PKG-04 — Traefik variant (documentation only)

**Acceptance Criteria**

- Provide an optional Traefik example config without being required by the stack.
- Explicitly document equivalences for:
  - media-auth subrequest behavior
  - header propagation

**Gates**

- `backend.lint`, `backend.tests` (docs lint optional later)

---

# EPIC PKG-EPIC-03 — TLS strategy (dev + prod)

## Outcome

- Dev TLS is automated and reproducible.
- Prod TLS has two supported paths (Docker Nginx+ACME, or K8s cert-manager), no mixed modes.

### PKG-05 — Dev TLS via mkcert (automated)

**Acceptance Criteria**

- A single command generates dev certs in a gitignored folder.
- Nginx uses those certs automatically in dev mode.

**Gates**

- `backend.lint`, `backend.tests` (plus optional “config validate”)

### PKG-06 — Prod TLS path A: K8s Ingress + cert-manager (documented)

**Acceptance Criteria**

- Document the required Ingress annotations and secret names.
- Ensure `DRIVE_PUBLIC_URL` matches the external hostname.

**Gates**

- `backend.lint`, `backend.tests`

### PKG-07 — Prod TLS path B: Docker Nginx edge + ACME (documented)

**Acceptance Criteria**

- Document ACME setup and certificate storage.
- No manual “copy/paste cert” steps.

**Gates**

- `backend.lint`, `backend.tests`

---

# EPIC PKG-EPIC-04 — Object storage endpoints: INTERNAL vs EXTERNAL (selfhost-proof)

## Outcome

- Explicit endpoint separation for object storage, validated by Drive-integrated CT-S3.

### PKG-08 — Document and validate INTERNAL/PROXY vs EXTERNAL/BROWSER endpoints

**Acceptance Criteria**

- Document:
  - INTERNAL: what proxy/backend uses (host signed == host used)
  - EXTERNAL: what browser uses for upload (after domain replace if used)
- CT-S3 invariants are part of the packaging validation checklist.

**Gates**

- `backend.lint`, `backend.tests`

---

# EPIC PKG-EPIC-05 — Backup/restore runbooks + smoke validation

## Outcome

- Minimal disaster recovery procedures are documented and testable.

### PKG-09 — Runbook: backup & restore (Postgres + object store + IdP config)

**Acceptance Criteria**

- Runbook covers:
  - Postgres backup/restore
  - object storage bucket(s) backup strategy
  - IdP/realm config export/import (dev reference)
- Redis is explicitly marked non-critical (rebuildable).

**Gates**

- `backend.lint`, `backend.tests`

### PKG-10 — Smoke test checklist post-restore

**Acceptance Criteria**

- A deterministic checklist validates:
  - login works
  - list files works
  - upload works
  - media access works (via media-auth)

**Gates**

- `backend.lint`, `backend.tests`

---

# EPIC PKG-EPIC-06 — Upgrade/rollback process (pinned images + migrations + gates)

## Outcome

- One standard upgrade flow with rollback capability.

### PKG-11 — Upgrade procedure (pin → migrate → gates → rollout)

**Acceptance Criteria**

- Document the sequence:
  - pin image versions
  - run migrations
  - run gates/smokes
  - rollout
- Clearly define rollback steps (previous image tags + DB state strategy).

**Gates**

- `backend.lint`, `backend.tests`

---

## Notes for PM handoff

- This is a Phase-3 draft (Idea Development). PM should convert epics/stories into the BMAD registry format with stable IDs and gates/test checklists.
- Packaging stories should avoid introducing new behaviors; they should formalize and validate existing deployment contracts.
