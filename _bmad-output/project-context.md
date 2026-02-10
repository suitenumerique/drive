# Project Context (AI/BMAD v6)

This repository is a fork of `suitenumerique/drive` and is intended to evolve as `Apoze/drive` with a strong self-host focus and a BMAD v6 agent-operable delivery process.

## 0) One-paragraph summary

Goal: ship a **production-usable self-hosted Drive** (Docker dev first, Docker or Kubernetes prod) while keeping the codebase close to upstream architecture (Django/DRF + Next.js) and preparing for a future **full “La Suite Numérique”** deployment (Docs/People/etc.) without forcing a “control panel” UI inside Drive.

Drive can run **standalone** (self-host) today, but it is designed to be integrated later into a broader suite (Docs/Messages/Calc/Meet/People/Find/...), primarily through shared identity, shared UI patterns, and operator tooling.

## 1) Non-negotiables (v1)

### Product / UX

- **Trust-first UX**: explicit states, actionable errors, no ambiguity.
- **No infinite loading**: long-running ops must be time-bounded and degrade to “still working / retry / contact admin / runbook link” without losing context.
- **Context-preserving**: after actions (upload/rename/share/WOPI/preview exit), return to the same folder/selection/view (scroll when feasible).
- **Capability-driven**: no dead actions; hide by default; show disabled only for discoverability and always with “why + next action”.
- **No-leak by design**: never display raw internal URLs/paths/keys/credentials; never show raw error objects or stack traces.
- **WCAG 2.1 AA no-regressions** baseline + a few targeted improvements on critical flows (Explorer keyboard/focus, modals, upload feedback).
- **No new UI component library** in v1 (reuse existing UI kit/tokens/patterns; tokens-only colors; no ad-hoc hex colors).

### Self-host / Ops

- **BYO OIDC IdP in production**: the final solution ships **without** an IdP. Dev may use Keycloak as a fixture.
- **Dev fixtures vs production reality**:
  - Development uses **Nginx + Keycloak** as convenient reference fixtures.
  - The final delivered solution is **bring-your-own** for both the edge proxy and the OIDC IdP.
- **Edge proxy is user-managed**: Nginx is the baseline reference; Traefik may be documented later, but the contract must remain proxy-agnostic.
- **S3-first core**: Drive content storage is S3-compatible object storage.
- **S3 provider baseline (Docker dev)**: **SeaweedFS S3 gateway** (MinIO replaced in this fork).
- **Kubernetes path**: plan to use **Ceph RGW** later (before any production data migration).
- **S3 contract-first correctness**: compatibility is proven with Drive-integrated contract tests (INTERNAL/PROXY vs EXTERNAL/BROWSER + connect_url vs signed_host).
- **SMB mount v1**: a second storage space inside the Explorer (MountProvider) with v1 scope: browse, upload (large files), preview, share links, WOPI/Collabora; no sync with S3; global mount permissions; path-based links may break on out-of-band changes.
- **Secret handling for mounts**: secrets are never stored as plain text in DB; use secret references + runtime resolution + hot rotation (no backend restart).

### Engineering process

- **English-only for code and code comments** (documentation may be bilingual if needed, but prefer English for agent-readability).
- **Small, extractible changes**: keep changes easy to review/cherry-pick; preserve the option to upstream later (human decision).
- **Fork-first automation (future)**: any automated GitHub actions by agents must target the fork only (`Apoze/drive`), never upstream.
- **Dev tooling note**: the repository `Makefile` is explicitly development-oriented (do not assume it is CI/prod-grade as-is).

## 2) Repository facts (current codebase)

### Tech stack

- Backend: Python + Django + Django REST Framework (WSGI), Celery worker(s), Redis, PostgreSQL.
- Frontend: TypeScript + React via Next.js (pages router), SCSS.
- Storage: S3 via `django-storages` + direct boto3 client usage in some flows.

### Local dev entrypoints (from `README.md` / `Makefile`)

- Bootstrap (dev): `make bootstrap`
- Run backend only: `make run-backend`
- Run all (backend + frontend container): `make run`
- Lint backend (dev): `make lint`
- Tests backend: `make test` / `make test-back`
- E2E (Playwright): `make run-tests-e2e -- --project chromium --headed` (example; see `Makefile`)

E2E intent for BMAD v6:
- Prefer **Chrome-only** runs for determinism (even if the product targets multiple browsers).

### Compose services & ports (development)

From `compose.yaml` (development defaults):

- Frontend (Drive): `http://localhost:3000`
- Backend API (Django): `http://localhost:8071` (container port 8000)
- Nginx (dev edge): `http://localhost:8083`
- Keycloak (dev IdP fixture): `http://localhost:8080` (configured to be used behind the edge proxy hostname)
- PostgreSQL: `localhost:6434`
- Keycloak PostgreSQL: `localhost:6433`
- Redis: `localhost:6379`
- SeaweedFS S3 gateway: `localhost:9000` (container 8333)
- ds-proxy: `localhost:4444` (optional profile)
- Collabora (dev): `http://localhost:9980`
- OnlyOffice (dev): `http://localhost:9981`

### Dev credentials (development fixtures only)

Defaults from `README.md` / `compose.yaml` (do not ship to production):

- App login: `drive` / `drive`
- Keycloak admin: `admin` / `admin`
- SeaweedFS S3: `AWS_ACCESS_KEY_ID=drive`, `AWS_SECRET_ACCESS_KEY=password`

## 3) Key contracts and “source of truth” behaviors

### 3.1 S3 audiences: INTERNAL/PROXY vs EXTERNAL/BROWSER

- **INTERNAL/PROXY**: what the edge proxy (or backend/proxy chain) calls when serving media.
- **EXTERNAL/BROWSER**: what the browser calls when uploading via presigned requests (including domain replacement when configured).

These audiences must be explicit in docs, diagnostics, and contract tests.

### 3.2 `/media` edge contract (auth subrequest + SigV4 replay)

- The edge proxy uses an auth subrequest to `GET /api/v1.0/items/media-auth/`.
- Backend returns SigV4 headers (at least):
  - `Authorization`
  - `X-Amz-Date`
  - `X-Amz-Content-SHA256`
  - optionally `X-Amz-Security-Token` (STS)
- Edge proxy forwards those headers to S3 when proxying `/media/...`.

### 3.3 Upload behavior (S3 baseline)

- Browser upload uses **presigned** request(s) returned by the API.
- After upload, the client calls `upload-ended` to finalize metadata and post-processing.

### 3.3.1 Upload sizing knobs (v1 requirement)

- Operators must be able to configure upload chunk/part sizing (S3 multipart and mount uploads where applicable), with documented defaults and limits.

### 3.4 WOPI / Collabora (v1 requirement)

- WOPI must be available for **eligible file types** when integration is **enabled and healthy**.
- For S3-backed WOPI, bucket **versioning** is required (current Drive behavior depends on `VersionId`).
- For MountProvider-backed WOPI (SMB), implement an application-level version string + locks (no dependency on S3 versioning).
- Development compose includes Collabora and OnlyOffice containers; v1 selfhost target is **Collabora Online via WOPI** (OnlyOffice is a dev fixture unless explicitly promoted later).
- Dev note: `compose.yaml` provisions the S3 bucket and enables versioning as part of the development bootstrap (see the `createbuckets` service).

## 4) SMB Mount v1 (functional scope)

SMB Mount v1 is implemented via a **MountProvider framework** (to be created). Some notes/drafts may use the term “MountDriver”, but there is no established “MountDriver” concept in the current codebase. To avoid confusion:
- Use **MountProvider** as the canonical name for this backend plugin boundary.
- Do not confuse it with the existing frontend “driver” concept (e.g., `StandardDriver`).

The SMB provider is the first concrete implementation.

SMB Mount is a **second root/workspace** in the Explorer (gateway semantics, no sync). Requirements:

- Browse/list directories and metadata (deterministic ordering + pagination/limits).
- Download via backend-mediated streaming (no full buffering requirement).
- Upload via backend-mediated streaming (large-file capable).
- Preview (capability-driven; explicit fallback when not supported).
- Share links for mounts:
  - Resource identity: `(mount_id, path)`
  - Accepted constraint: links may break if renamed/moved/deleted out-of-band
  - Error semantics (MountProvider share links):
    - `404` invalid/unknown token
    - `410` valid token but target missing (out-of-band change)
- WOPI/Collabora works on SMB via gateway semantics (locks + version string), with explicit states (no infinite loading).

Mount permissions:
- Single SMB service account is used to access the share.
- Drive enforces user permissions at the application layer (global mount-level permissions are acceptable in v1).
- Users may bypass Drive ACLs by using SMB directly (accepted).

## 5) Diagnostics (suite-ready, API-first)

v1 UX placement: **Explorer right panel** (non-invasive). Long-term suite placement: external control panel tooling.

Invariants:

- Diagnostics are **API-first** and return the **same payload shape** an external “Control Panel” would consume (no parallel logic in the right panel).
- Payload must include both audiences (INTERNAL/PROXY and EXTERNAL/BROWSER) side-by-side; “overall worst-of” may be derived but must not hide per-audience truth.
- Evidence is **safe evidence only** (allow-list), no raw sensitive paths/keys/credentials.
- Actions are capability-driven and may be 0/1/2 visible:
  - Export support bundle (no-leak)
  - Open in external Control Panel (future)

## 6) Contract tests (CT-S3) — v1 must-have set

Drive-integrated S3 contract tests (IDs are stable; exact implementation TBD):

- CT-S3-001: INTERNAL media-auth signed GET works
- CT-S3-003: EXTERNAL presign targets browser host
- CT-S3-004: EXTERNAL PUT via presigned succeeds (requires `x-amz-acl: private` when signed)
- CT-S3-006: INTERNAL Range path used by app works (optionally strict 206 micro-test)
- CT-S3-007: INTERNAL Copy + `MetadataDirective=REPLACE` updates ContentType (with retry/backoff)
- CT-S3-008: INTERNAL special chars in key (spaces, &)
- CT-S3-010: host signed == host used, per target (connect_url vs signed_host pattern)

Provider profiles:

- `seaweedfs-s3`: **blocking** for v1 (baseline)
- `ds-proxy`: optional / non-blocking (recorded, can be quarantined)
- `ceph-rgw`: future profile

## 7) “Where to look” (high-signal file pointers)

Backend:

- Media auth + upload-ended: `src/backend/core/api/viewsets.py`
- S3 signing + presign policy: `src/backend/core/api/utils.py`
- Existing media-auth test(s): `src/backend/core/tests/items/test_api_items_media_auth.py`
- Upload policy tests: `src/backend/core/tests/items/test_api_items_children_create.py`

Proxy templates:

- Dev Nginx: `docker/files/development/etc/nginx/conf.d/default.conf`
- Prod Nginx: `docker/files/production/etc/nginx/conf.d/default.conf`
- Keycloak realm (dev fixture): `docker/auth/realm.json`
- Helm examples: `docs/examples/helm/drive.values.yaml`
- Note: Helm examples include MinIO values (`docs/examples/helm/minio.values.yaml`); this fork’s Docker baseline uses SeaweedFS and may require Helm example adjustments later.

Frontend:

- Upload driver (presign + XHR PUT): `src/frontend/apps/drive/src/features/drivers/implementations/StandardDriver.ts`
- Upload orchestration + toast: `src/frontend/apps/drive/src/features/explorer/hooks/useUpload.tsx`
- WOPI editor: `src/frontend/apps/drive/src/features/ui/preview/wopi/WopiEditor.tsx`
- File share modal (placeholder exists): `src/frontend/apps/drive/src/features/explorer/components/modals/share/FileShareModal.tsx`

Docs in this fork:

- Self-host review / decisions: `_bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md`
- Playwright + Chrome + Docker guidance: `_bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md`

## 8) Execution intent (historical BMAD v6 notes)

These notes were written for a BMAD v6 “agent-operable” execution plan. Current work is expected to proceed via normal development workflow and Codex conversations, while keeping `_bmad-output/` as a high-signal local knowledge base.

- PRD is complete and coherent (FR/NFR + success criteria + domain requirements).
- UX specification is complete (steps 1–13) and all Mermaid diagrams render correctly.
- Storage decisions are locked (SeaweedFS baseline; Ceph RGW later; SMB mount v1 scope).
- Contract-test plan is explicit (CT-S3 IDs, audiences, profiles, failure_class taxonomy, safe evidence allow-list).
- Agent-operable gating plan exists (diff→gates mapping, artifacts, no-leak scanning scope, quarantine policy).

Recommended artifact root (create when ready): `_bmad-output/`

- `_bmad-output/planning-artifacts/` (PRD, UX spec, backlog snapshots)
- `_bmad-output/implementation-artifacts/` (test reports, diagnostics exports, bundles — no-leak)

Recommended practice:
- Files under `_bmad-output/**` are the **source of truth** for planning decisions (PRD/UX/epics/artifacts).
- GitHub issues/PRs may mirror those decisions for collaboration, but this is manual and not strictly enforced by automation.

## 9) Open questions (keep short; do not block v1)

- Exact UX placement and navigation for SMB mount root in Explorer (tree node vs workspace grouping).
- Exact “Control Panel” ecosystem integration target (which suite component consumes the diagnostics payload first).
- Whether Traefik edge support requires a dedicated media gateway (keep as future validation; Nginx is baseline).

## 10) Git remotes & branching (fork-first)

This project is developed as a **fork**:

- `origin` must point to `Apoze/drive` (the fork).
- If an `upstream` remote exists, it must be **read-only** for humans and **never used** by automation/agents.
- Any agent automation using `gh` must target the fork only (e.g., `-R Apoze/drive` or `GH_REPO=Apoze/drive`).

Recommended branch naming (BMAD):

- Work branches: `bmad/<work_id>-<slug>` (example: `bmad/PR2-1-signed-access-targets`)
- Optional long-lived branch for integration: `selfhost/main` (keep `main` tracking upstream patterns if desired)

## 11) Glossary (avoid vocabulary drift)

- **Audience (S3)**: a distinct network/host context used for S3 operations.
  - **INTERNAL/PROXY**: the host/endpoint the edge proxy uses to fetch media from S3.
  - **EXTERNAL/BROWSER**: the host/endpoint the browser uses for presigned uploads (domain replacement may apply).
- **connect_url vs signed_host**: contract-test pattern where tests connect to a reachable URL while sending the `Host` header that was actually signed (HTTP-only in general).
- **safe evidence**: an allow-listed set of diagnostic fields (e.g., status codes, request_id, hashes) that is safe to show/export without leaking secrets/paths/keys.
- **failure_class**: a stable, machine-readable classification for failures (used for triage + next actions; not a severity).
- **mount_id**: stable identifier for a mount configuration (MountProvider).
- **mount path**: the path inside the mounted backend (e.g., SMB share subpath) used for mount resources and share links.
