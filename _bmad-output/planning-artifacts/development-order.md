---
generated: "2026-02-08"
source: "_bmad-output/planning-artifacts/epics.md"
note: "Epic numbering is thematic; this file provides a dependency-based execution order."
---

# Recommended Development Order (v1)

## Non-negotiable constraints to keep in mind (shape the order)

- **Docker-first v1** is the baseline; **K8s remains reference-only (as-is)** with **no v1 improvements/gates**.
- **SeaweedFS is the Sprint 0 baseline** for the blocking S3 provider profile (MinIO may remain as a non-blocking fixture only).
- **WOPI v1 is Collabora-only**; **OnlyOffice stays untouched** (do not remove, add, or expand it).
- **No-leak** is mandatory: client responses stay generic; actionable details live only in operator-facing diagnostics/artifacts with allow-listed evidence.

## Sprint 0 — Foundations (deployability + baseline correctness + deterministic gates)

1. **Epic 11 / Story 11.2** — Make SeaweedFS the *real* default baseline (compose/runbooks/gates aligned; MinIO not treated as baseline).
2. **Epic 1 / Story 1.1** — Canonical `DRIVE_PUBLIC_URL` validation + deterministic derivations (includes dev-only insecure HTTP override pattern).
3. **Epic 2 / Story 2.3** — TLS posture for *all public surfaces* (prod HTTPS-only, dev override explicit, no mixed modes, normalization).
4. **Epic 1 / Story 1.2** — Separate allowlists (redirect URIs vs origins/hosts), derived from the canonical public URL (no wildcards).
5. **Epic 2 / Story 2.1** — Docker-first edge contract docs + configuration validation + deterministic checklist + optional smoke endpoints (no proxy “inspection” promises).
6. **Epic 2 / Story 2.2** — Nginx reference config for `/media` `auth_request` + SigV4 propagation (incl. “no logging/echo of SigV4 secrets”).
7. **Epic 11 / Story 11.1** — Drive-integrated CT-S3 runner (audiences `INTERNAL_PROXY`/`EXTERNAL_BROWSER`) + deterministic reports.
8. **Epic 11 / Story 11.3** — Safe evidence allow-listing for CT-S3 (no-leak by construction).
9. **Epic 12 (optional)** — Lightweight “gates” as `make`/CI targets (stable IDs + deterministic artifacts), without any one-shot orchestrator dependency.
10. **Epic 12 (optional)** — Standardize `failure_class` + `next_action_hint` schema across operator-facing artifacts and docs.
11. **Epic 12 (optional)** — Wire CT-S3 + no-leak checks + docs consistency (“mirror”) + mounts-related checks into CI as separate gates (blocking vs non-blocking made explicit).
12. **Epic 2 / Story 2.4** — Backup/restore runbook + deterministic post-restore smoke checklist (BYO IdP; preserve bucket layout/prefixes).
13. **Epic 2 / Story 2.5** — Upgrade/rollback runbook + deterministic ordering + smoke checklist (pin/pull → migrate → restart → smoke; rollback may require DB restore).

## Sprint 1 — Identity + policy (unblocks all authenticated flows)

1. **Epic 3 / Story 3.1** — BYO OIDC auth (refs-only secrets; deterministic precedence; smoke proof beyond “login page”).
2. **Epic 3 / Story 3.2** — Entitlements enforcement (API + UI gating; no dead actions).
3. **Epic 3 / Story 3.3** — External API allowlist (action-level, strict, no wildcards).
4. **Epic 3 / Story 3.4** — Resource Server mode (disabled by default; introspection-based validation; deterministic 401/403; client-generic errors).

## Sprint 2 — Core S3 experience + resilience patterns (build once, reuse everywhere)

1. **Epic 5 / Story 5.2** — No-leak error contract (generic client responses; operator artifacts carry `failure_class` + safe evidence).
2. **Epic 5 / Story 5.1** — Time-bounded long-running states (upload, preview, WOPI launch, public share open, diagnostics refresh).
3. **Epic 4 / Story 4.1** — Browse/navigate with deterministic ordering/pagination + abilities/capabilities in the list contract.
4. **Epic 4 / Story 4.2** — Create folder (capability-driven; clean validation/no-leak).
5. **Epic 4 / Story 4.6** — Operator-configurable upload part/chunk sizing (validated + normalized deterministically; clear scope).
6. **Epic 4 / Story 4.3** — Presigned upload flow (EXTERNAL_BROWSER audience; deterministic pending/failure semantics; idempotent retry).
7. **Epic 5 / Story 5.3** — Deterministic recovery patterns (pending TTL documented; cleanup without phantom items; actionable states).
8. **Epic 4 / Story 4.4** — Download via media edge contract (range support where applicable).
9. **Epic 4 / Story 4.5** — Preview (deterministic availability; “not available” distinct from “access denied”).

## Sprint 3 — Share links (S3) + public no-leak semantics

1. **Epic 6 / Story 6.1** — Configure share links for S3 items.
2. **Epic 6 / Story 6.2** — Open S3 public share links without an authenticated session (token enforced; client-generic errors).

## Sprint 4 — WOPI/Collabora (S3 first), then mount-backed WOPI later

1. **Epic 10 / Story 10.1** — WOPI enablement/config/host allowlist/HTTPS posture/health gating (Collabora-only).
2. **Epic 10 / Story 10.2** — Capability-driven WOPI action exposure (no dead buttons).
3. **Epic 10 / Story 10.3** — Reverse-proxy-compatible WOPI launch flow (short-lived tokens).
4. **Epic 10 / Story 10.4** — S3 prerequisites validation (bucket versioning) with operator guidance.

## Sprint 5 — Mount framework + secrets (contract-level first; no admin UI)

1. **Epic 7 / Story 7.1** — Mount registry + deterministic validation (refs-only secrets).
2. **Epic 8 / Story 8.1** — Enforce refs-only secrets (never store/return/log secret material).
3. **Epic 8 / Story 8.2** — Centralized secret resolver (file > env precedence; bounded refresh).
4. **Epic 8 / Story 8.3** — Safe session reuse across rotation (no stale creds; no leaks).
5. **Epic 7 / Story 7.2** — Discover mounts + capabilities (constants enforced).
6. **Epic 7 / Story 7.3** — Browse mounts (deterministic ordering/pagination; virtual entry identifiers).
7. **Epic 7 / Story 7.4** — Capability gating across mount actions (no dead actions; deterministic errors).
8. **Epic 7 / Story 7.5** — Create MountProvider share links (capability-driven).
9. **Epic 7 / Story 7.6** — Public MountProvider share semantics (invalid token → 404; missing target → 410; no-leak).

## Sprint 6 — SMB provider (implementation-level, built strictly on the framework)

1. **Epic 9 / Story 9.1** — SMB configuration schema + deterministic validation (refs-only secrets).
2. **Epic 9 / Story 9.2** — Implement mount browse contract (no duplicate “browse” logic outside the framework).
3. **Epic 9 / Story 9.3** — Streaming download (+ range where applicable).
4. **Epic 9 / Story 9.4** — Streaming upload (large-file capable; deterministic finalize semantics).
5. **Epic 9 / Story 9.5** — Preview support (explicit, capability-driven, deterministic).

## Sprint 7 — Mount-backed WOPI (only after mounts + SMB flows are proven)

1. **Epic 10 / Story 10.5** — MountProvider WOPI semantics (version string, locks, streaming save pipeline, no-leak).
