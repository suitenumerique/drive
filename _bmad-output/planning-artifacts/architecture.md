---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/product-brief-drive-20260203-200136.md
  - _bmad-output/planning-artifacts/architecture/architecture-kickoff-brief.md
  - _bmad-output/project-context.md
  - _bmad-output/brainstorming/brainstorming-session-20260203-110252.md
  - docs/architecture.md
  - docs/ds_proxy.md
  - docs/entitlements.md
  - docs/env.md
  - docs/installation/README.md
  - docs/installation/kubernetes.md
  - docs/metrics.md
  - docs/release.md
  - docs/resource_server.md
  - docs/setup-find.md
  - docs/theming.md
  - _bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md
  - _bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md
  - _bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md
  - _bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md
  - _bmad-output/planning-artifacts/handoff/brainstorming-handoff.md
  - _bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md
  - _bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md
  - _bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md
  - _bmad-output/planning-artifacts/upstream/upstream-triage-v1.md
  - _bmad-output/planning-artifacts/upstream/upstream-triage-v1.yaml
  - _bmad-output/planning-artifacts/upstream/drive-open-backlog.md
  - _bmad-output/planning-artifacts/upstream/drive-open-issues.json
  - _bmad-output/planning-artifacts/upstream/drive-open-prs.json
workflowType: 'architecture'
project_name: 'drive'
user_name: 'Apoze'
date: '2026-02-04T23:15:40Z'
document_output_language: English
communication_language: Français
lastStep: 8
status: 'complete'
completedAt: '2026-02-05T12:33:36Z'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (PRD – 54 FRs across 9 categories):**
- **Identity, Access & Policy:** BYO OIDC IdP; entitlements-driven access (`can_access`, `can_upload`); external API / resource-server mode for suite integrations.
- **Core File Experience (S3-first baseline):** browse/create folders/upload/download/preview/share with reliability and actionable, no-leak diagnostics.
- **MountProvider Framework + SMB mount v1:** introduce a plugin-like **MountProvider** boundary to add an SMB “second space” inside the Explorer (no sync with S3), including browse, streaming upload/download, preview, share links, and WOPI.
  - Mount features are **capability-driven by contract** (capability keys to introduce and standardize in this project, e.g. `mount.upload`, `mount.preview`, `mount.wopi`): actions are available when the capability is true and prerequisites are satisfied.
- **Mount secrets:** secret references + runtime resolution + hot rotation; secrets never stored/returned/logged.
- **Share links:** must support MountProvider resources `(mount_id, path)` with explicit semantics:
  - `404` = invalid/unknown token
  - `410` = valid token but target missing (out-of-band move/delete accepted)
  - Responses must be **clean (no stack traces)** and **no-leak** (safe copy / user-facing messaging).
- **WOPI / Collabora (product intent):** WOPI is **expected** to be available for any storage backend (S3 or MountProvider) **when**:
  - the file is eligible, and
  - the integration is enabled **and healthy** (including discovery and reverse-proxy reachability at a product level, without prescribing implementation), and
  - backend prerequisites are satisfied (e.g., S3: versioning prerequisite; mounts: version string + locks + save pipeline).
  Capability-driven here means “explicit prerequisites & health gating”, not “optional”.
- **Self-host Packaging & Edge Contracts:** canonical `DRIVE_PUBLIC_URL`; proxy-agnostic edge contract (Nginx reference) including `/media` auth subrequest + SigV4 header propagation; TLS strategy; backup/restore and upgrade/rollback runbooks.
- **Storage Correctness:** Drive-integrated CT-S3 with explicit audiences INTERNAL/PROXY vs EXTERNAL/BROWSER and `connect_url` vs `signed_host` invariants.
- **Automation / Deterministic Gates / Strict Mirror:** stable `gate_id`s, deterministic artifacts, `failure_class` taxonomy + `next_action_hint`, and strict mirror enforcement (registry fingerprint B+ in issues/PRs).
  - **Source of truth:** BMAD local artifacts/registry are the source of truth; GitHub issues/PRs on the fork are a strict mirror only.

**Non-Functional Requirements (PRD – 10 NFRs):**
- **Streaming & efficiency:** backend-mediated transfers (MountProvider, WOPI save) must stream (no full buffering).
- **Deterministic failure reporting:** stable `failure_class` + `next_action_hint` in artifacts for any failing gate.
- **Operability runbooks:** deterministic smoke checklist for post-restore/post-upgrade validation.
- **Security / no-leak:** global no-leak for APIs/logs/artifacts; automated scanning scope limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`).
- **TLS & proxy reality:** production must support HTTPS and a proxy-agnostic edge contract (Nginx as reference).
- **Accessibility:** WCAG 2.1 AA “no regressions”.
- **Compatibility:** remain compatible with external OIDC IdPs; preserve `/media` auth_request contract and SigV4 header propagation (including optional STS token).

**UX-driven architectural implications (UX spec + project-context non-negotiables):**
- Trust-first UX: explicit states, actionable errors, “no infinite loading” (time-bounded long-running ops).
- Context-preserving navigation after actions (upload/share/WOPI/preview).
- Capability-driven UI (no dead buttons; explain “why” + “next action”).
- No new UI component library in v1; reuse existing UI kit/tokens/patterns.
- **Suite-ready diagnostics:** diagnostics must be **API-first** with a stable payload model consumable by a future Suite “Control Panel”; Drive’s UI is a renderer of that payload (no parallel logic), while Drive remains standalone but integrable later (Docs/Messages/Calc/etc.).

**Scale & Complexity:**
- Primary domain: self-hosted web app (Next.js SPA-like) + Django/DRF backend, with strong ops/testing automation requirements.
- Complexity level: **High** (brownfield + multi-service dependencies + proxy/storage/WOPI integrations + strict mirror workflow).
- Architectural building blocks implied (estimate): ~10–14 cross-cutting components.

### Technical Constraints & Dependencies

- **Repo & process scope (fork-only safety rails):**
  - Implementation and GitHub automation happen **only** in `Apoze/drive`.
  - BMAD local artifacts/registry are the source of truth; fork issues/PRs are mirror only.
  - No upstream GitHub access/operations by agents; upstream is **reference-only** via a frozen local snapshot under `_bmad-output/planning-artifacts/upstream/`.
  - `origin` must point to the fork; any `upstream` remote must be treated as read-only by humans and never used by automation.
  - Explicitly forbid any automation path that could push to upstream (delivery-system constraint).
- **Dev fixtures vs production reality:** Keycloak and Nginx are dev/reference fixtures; production is bring-your-own OIDC IdP and bring-your-own reverse proxy conforming to the edge contract.
- **Stack constraints:** Django/DRF + Celery + Redis + Postgres; Next.js frontend; S3-compatible storage as core.
- **Edge/media contract:** `/media` auth subrequest + SigV4 header propagation is a hard integration point.
- **Storage correctness model:** explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER) and `connect_url` vs `signed_host` invariants; provider profiles include a blocking baseline (SeaweedFS S3 gateway) and optional profiles (ds-proxy).
- **MountProvider/SMB constraints:** gateway model (backend-mediated), global mount permissions, no sync with S3, path-based share links may break on out-of-band changes.
- **Deterministic delivery constraints:** gate IDs, artifacts under `_bmad-output/implementation-artifacts/`, strict mirror fingerprint B+ for issues/PRs, quarantine policy for flakiness.

### Cross-Cutting Concerns Identified

- **No-leak everywhere:** safe evidence allow-listing; redaction and logging policy across backend, runner, and UI messaging.
- **Capability-driven product surface:** shared capability vocabulary across backend APIs and frontend UI (including MountProvider and WOPI).
- **Audience-aware networking:** consistent modeling of “who calls what host” (browser vs edge vs backend) for S3/media flows and diagnostics.
- **Determinism & reproducibility:** stable gates, stable failure taxonomy, reproducible artifacts, Chrome-only E2E strategy.
- **Upstreamability as a constraint:** small extractible changes, provider-neutral boundaries, minimize divergence.

## Starter Template Evaluation

### Primary Technology Domain

Brownfield web application repository (Django/DRF backend + Next.js frontend) with self-host packaging, proxy/media contracts, storage correctness (CT-S3), MountProvider extensibility (SMB), WOPI integration, and deterministic delivery constraints (gates/artifacts/strict mirror).

### Starter Options Considered

1) **Use the existing `Apoze/drive` repository as the foundation (Selected)**
- Rationale: preserves upstream-like architecture, minimizes divergence, keeps all existing contracts (OIDC, `/media` auth_request + SigV4 propagation, S3 flows), and aligns with strict-mirror / deterministic gates delivery.

2) **Re-scaffold with a new “starter template” (Rejected)**
- Rationale: would create unnecessary churn in a brownfield codebase and increase divergence risk; conflicts with the goal of keeping changes extractible and upstream-friendly.

### Selected Starter: Existing Drive repository baseline (no re-scaffold)

**Rationale for Selection:**
- The repository already defines the required foundations: Django/DRF + Next.js architecture, Docker-compose dev stack, existing routing/contracts, and tooling that must be preserved for self-host v1.
- New work should fit into the existing structure and the BMAD delivery system (gates/artifacts/strict mirror), rather than resetting project structure via a generator.

**Initialization Command (dev bootstrap):**

```bash
make bootstrap
```

**Note:** The repository `Makefile` is explicitly development-only (not CI/production-grade). It is a dev bootstrap entrypoint, not a production initialization procedure.

**Architectural Decisions Provided by the Existing Baseline:**

**Language & Runtime (repository constraints):**
- Backend: Python 3.13 (`requires-python ~=3.13.0`), Django constrained to `<6.0.0`, build backend `uv_build`.
- Frontend (Drive app): Node `>=22 <25`, Yarn `1.22.22`, Next `15.4.9`, React `19.2.0`.

**Styling Solution:**
- Existing SCSS and token-driven styling (no new component library in v1).

**Build Tooling:**
- Docker Compose dev stack + Makefile workflows (development-oriented).
- Backend uses `uv_build` and the existing lint/test commands.

**Testing Framework:**
- Backend: pytest (+ pytest-django) with ruff/pylint.
- Frontend unit tests: Jest (Drive app).
- E2E: Playwright Test exists as a dedicated workspace app at `src/frontend/apps/e2e` (invoked via the repo’s Makefile E2E targets).
- Chrome-only runs are the determinism target for v1 E2E, but should be treated as an intent unless/until wired as a CI gate.
- Playwright MCP may be available depending on the host environment, and can be used for interactive debugging when present.

**Code Organization:**
- Follow current Django app boundaries and Next.js app structure; introduce new subsystems (MountProvider, contract tests, gates runner) as additive, clearly bounded modules.

**Development Experience:**
- Repeatable dev bootstrap and run targets; artifacts and diagnostics should be designed to integrate with the BMAD `_bmad-output/**` conventions.

**Note:** There is no “create new project” CLI command for this effort. The first implementation work should focus on establishing deterministic gates/artifacts and safe, additive module boundaries inside the existing repository.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Data architecture for mounts and secrets (static mount config, secret resolution + rotation, mount entry identity).

**Important Decisions (Shape Architecture):**
- Cache/locks baseline and shared semantics for WOPI (including SMB WOPI trajectory).

**Deferred Decisions (Post-MVP):**
- Mount CRUD/admin management in DB/UI (v2+).

### Data Architecture

- Primary relational database: PostgreSQL (existing baseline; DB schema evolves via Django migrations only).
- Migrations: Django migrations (single source of schema evolution).
- Cache/locks: Django cache backed by Redis; WOPI locks use cache keys with TTL (current baseline), and SMB-WOPI follows the same lock semantics.
- Mount configuration (v1): mounts are declared in static configuration (settings/env), not stored or managed via DB CRUD.
  - Important: this remains compatible with “rotate password without restart” because the mount definition stays stable while the resolved secret value can change.
- Mount secrets (v1): secrets are reference-only (no secret material stored in DB); runtime resolution with deterministic precedence and hot rotation support.
  - Contractual mechanisms: env ref + file path ref
  - Deterministic precedence (recommended): `password_secret_path` (file) > `password_secret_ref` (env var name)
  - Rotation without restart: secret resolver uses a bounded-time refresh (e.g., polling + TTL cache and/or file watcher), so updated secret values are picked up without changing mount definitions.
- Mount resource identity: canonical representation is `(mount_id, normalized_path)`; diagnostics/evidence may use `path_hash` (no-leak) instead of raw paths.

### Authentication & Security

- **OIDC authentication (v1):** keep `mozilla-django-oidc` as the OIDC mechanism; production is **BYO OIDC IdP** (Keycloak may be used as a dev/reference fixture only).
- **Authorization / policy (capability gating):** entitlements are the canonical pattern (`can_access`, `can_upload`, and extensible `can_*` methods) and are the foundation for API/UI capability gating.
- **Resource server / External API:** strict allowlist, **disabled-by-default**; only explicitly listed endpoints/actions are exposed.
- **Secrets management (v1):**
  - Global rules for **all** secrets (DB/S3/OIDC/etc.): no secrets in git; secrets are never returned by APIs; no-leak in logs/artifacts and in 4xx/5xx errors.
  - **Refs-only** is recommended globally.
  - **Rotation without restart:** **must-have** for MountProvider secrets (SMB) and S3 credentials; best-effort elsewhere (restart may be acceptable for some secrets like DB DSN).
  - For MountProvider secrets (and S3 creds when applied): support env ref + file path ref with deterministic precedence and bounded-time refresh.
- **No-leak enforcement (architecture rule):** safe-evidence allow-list + `failure_class` (+ `next_action_hint`) across backend, artifacts, and user/operator-facing surfaces; automated scanning scope limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) only.
- **WOPI security & health gating:** host allowlist derived from `DRIVE_PUBLIC_URL`, short-lived tokens, lock TTLs; “enabled & healthy” explicitly includes discovery reachability and reverse-proxy contract correctness (without prescribing how). UI must always render an actionable state when disabled/unhealthy/prerequisites missing.

### API & Communication Patterns

- **Internal API style (v1):** REST API built with Django REST Framework using resource-based endpoints plus explicit actions (viewsets/actions). GraphQL is out of scope for v1.
- **Mount browsing contract (v1):** limit/offset pagination with a standardized deterministic ordering, documented and implemented consistently across API and UI.
  - Ordering rule (example contract): folder-first, then casefolded name, then a **stable, unique** tie-breaker (e.g., `normalized_path`) to prevent collisions when multiple entries share the same display name.
  - Guardrail: ordering is **not client-controlled** unless an explicit allowlist is introduced (to preserve determinism and prevent API/UI/backend-specific divergence).
- **Mount “virtual entry” representation (v1):** responses identify entries using `(mount_id, normalized_path)` plus `entry_type` and the minimal UI-relevant metadata, without exposing SMB connection details (server/share) or raw backend paths.
- **Transfer semantics (v1):**
  - S3 uploads remain browser-side presigned flows.
  - Any backend-mediated transfers (MountProvider downloads/uploads, WOPI save pipeline) must be streaming (read/write chunks) with a strict “no full buffering” rule.
- **Mount share links semantics (v1):** strict contract for clean, no-leak errors:
  - `404` for invalid/unknown token
  - `410` for valid token with missing target (out-of-band move/delete accepted)
  - Explicit rule: never return stack traces; always return a clean error response.
  - Public share-link endpoints must **never** reflect any path (including `normalized_path`) or SMB info in errors; use generic messaging plus `failure_class` and `next_action_hint` when helpful.
- **Error handling standard (v1):** use a stable error format (drf-standardized-errors), and include `failure_class` + `next_action_hint` when relevant.
  - Note: `failure_class` is a code identifier, not a severity; severity is derived from status and audience context (e.g., INTERNAL/PROXY vs EXTERNAL/BROWSER).
  - Scope nuance (anti-rework): mandatory for new surfaces (mounts, diagnostics, CT-S3 runner outputs, WOPI gating, mount share-link endpoints), without requiring a big-bang refactor of all legacy endpoints.
- **API documentation (v1):** OpenAPI via drf-spectacular as the internal contract for aligning UI and future Suite “Control Panel” consumers.

### Frontend Architecture

- **State management (v1):**
  - Server-state: React Query.
  - UI state: local state and React Context.
  - No new global state library (Redux/Zustand) in v1 unless explicitly justified by a concrete need.

- **Capability-driven UI contract (v1):**
  - “No dead actions” everywhere (MountProvider/mounts, WOPI, diagnostics, share links).
  - Default behavior: hide unavailable actions.
  - Disabled actions are shown only when needed for discoverability, and must always include “why” + “next action”.

- **Error & status surfaces (v1):**
  - Time-bounded long-running states (“still working / retry / contact admin / runbook link”), never infinite loading.
  - Upload feedback via toasts; consistent banners/panels for degraded/unavailable features.
  - Render `failure_class` + safe evidence + `next_action_hint` in a stable, no-leak way.
  - Never render raw errors or stack traces in the UI.

- **Routing / surfaces (v1):**
  - Keep existing patterns: Explorer + right panel + modals; no Settings/Admin area in v1.
  - Diagnostics UI is in the Explorer right panel for v1 and is **API-first**:
    - it renders a stable payload shape consumable by a future Suite Control Panel,
    - Drive is a renderer (no parallel logic), and the Control Panel is out of scope for this project.

- **E2E strategy (v1):**
  - Product requirement: compatibility across Chrome/Edge/Firefox (e.g., last 2 major versions). WebKit/Safari is not a v1 product requirement.
  - Capability: Playwright suite must remain multi-browser runnable (Chromium/Firefox/Edge where available; WebKit may remain best-effort/non-blocking).
  - CI gating pragmatism:
    - Blocking on PR: a single reference browser (Chrome/Chromium) to reduce flakiness.
    - Non-blocking scheduled runs: additional browsers (Firefox + Edge) with reporting + quarantine policy.
    - “Chrome-only determinism” is a target for the blocking gate; CI wiring may follow.

### Infrastructure & Deployment

- **Production deployment (v1):** Docker (single-machine) is the baseline for v1 self-host, with operator runbooks as first-class deliverables. Kubernetes remains a documented trajectory, not “K8s-only”.
  - v1 scope is Docker-first only: runbooks, Nginx edge templates, prod TLS (ACME), and backup/restore/upgrade procedures target Docker/mono-machine.
  - Kubernetes is out of scope for v1 hardening: keep existing K8s docs/files as reference “as-is”, without new guarantees or dedicated v1 gates/contract tests.
- **Edge proxy:** user-managed reverse proxy; Nginx is the contractual reference implementation. Other proxies are acceptable if they conform to the documented edge contract (Traefik notes later; no dependency).
- **Canonical public URL:** `DRIVE_PUBLIC_URL` is the single source of truth for all public-facing host derivations (redirects, share links, WOPI allowlist, CORS origins), with explicit operator-configurable exceptions when needed (e.g., IdP requirements).
- **TLS (v1):** production HTTPS is mandatory (no mixed TLS modes). Dev TLS may use mkcert; production TLS can be provisioned via ACME (Docker) or cert-manager (K8s) depending on operator context.
- **S3 provider profiles (v1):** SeaweedFS S3 gateway is the blocking baseline profile for Docker/selfhost; ds-proxy is non-blocking (quarantine allowed); Ceph RGW is a future Kubernetes profile to adopt before any production data migration.
- **CI/CD and gates (v1):** deterministic gates runner + artifacts under `_bmad-output/implementation-artifacts/`; strict mirror fingerprint B+ verification in CI; no-leak scan limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) only.
- **Observability (v1):** structured logs + correlatable `request_id` in safe evidence, without imposing an external observability stack (Prometheus/ELK) in v1.
  - Keep hooks/exports compatible with operator-owned tooling (e.g., existing metrics endpoint when enabled), but treat full observability stack as operator-owned.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** naming, API shapes, secret resolution/rotation, no-leak evidence, WOPI/mount capability gating, deterministic artifacts/gates, strict-mirror boundaries.

### Naming Patterns

**Database / Django**
- Use Django defaults for table/column naming; do not introduce custom DB naming schemes in v1.

**MountProvider / Mounts**
- Canonical identifiers:
  - `mount_id` (string, stable, config-defined)
  - `normalized_path` (POSIX-style normalized path inside a mount)
  - `path_hash` (diagnostics/evidence only; never replace `normalized_path` in authenticated browse)
- Capability keys (v1 minimum set):
  - `mount.upload`, `mount.preview`, `mount.wopi`, `mount.share_link`
- Rule: capability keys are **documented constants**; no ad-hoc strings in UI/backend.
- Secret fields (config):
  - `password_secret_path` (file path) and `password_secret_ref` (env var name)
  - Precedence is deterministic: `password_secret_path` > `password_secret_ref`

**Audience codes**
- Audience codes are **constants** and must not drift across CT-S3, diagnostics payload, docs, and UI:
  - `INTERNAL_PROXY`
  - `EXTERNAL_BROWSER`
- UI labels may be human-friendly (e.g., “Internal (proxy)” / “External (browser)”), but the underlying codes above must remain unchanged.

**Gates / Artifacts / Mirror**
- Gate IDs are stable strings (e.g., `backend.tests`, `mounts.integration.smb`, `s3.contracts.seaweedfs`), never raw commands in registry.
- Failure classes use **exactly 3 segments**: `domain.category.reason`
  - Segments are separated by `.` and **each segment is `snake_case`**.
  - Example: `s3.signature.host_mismatch`.
  - Note: avoid encoding audience in `failure_class` when the audience is already carried separately (e.g., `INTERNAL_PROXY` / `EXTERNAL_BROWSER`) to prevent redundancy; if a case truly requires it, ensure there is a single source of truth (no conflicting duplication).

### Structure Patterns

**Backend**
- New subsystems are additive and bounded:
  - MountProvider-related code is grouped under a single bounded package boundary (no scattering across unrelated modules).
  - Secret resolution logic is centralized (one resolver, used consistently).
  - Diagnostics payload generation is centralized and API-first.
- Tests:
  - New backend behavior must ship with pytest tests (unit + integration where applicable), following existing test layout conventions.

**Frontend**
- No new UI component library in v1; reuse existing UI kit/tokens/patterns.
- Diagnostics UI is a renderer of the API payload (no duplicated business logic).

### Format Patterns

**API response shapes**
- Mount browse/list endpoints:
  - Deterministic ordering and limit/offset pagination are part of the contract.
  - Ordering is not client-controlled unless an explicit allowlist is introduced.
- Virtual entries are represented via `(mount_id, normalized_path)` + minimal metadata; never expose SMB connection details (server/share) or raw backend paths.

**Error responses**
- Use `drf-standardized-errors` format for new surfaces.
- Include `failure_class` + `next_action_hint` when relevant.
- `failure_class` is a code identifier, not a severity (severity derives from status and audience context).

**Share link errors (public)**
- Mount share links:
  - `404` invalid/unknown token
  - `410` valid token but target missing
  - Responses are **generic and no-leak**.
  - Never return stack traces.
  - Never reflect any path (including `normalized_path`) or SMB details in public share-link errors (generic message + failure_class + next_action_hint if needed).

**No-leak evidence**
- “Safe evidence” is allow-listed (status codes, request_id, keyed hashes, latency buckets).
- `path_hash` must be computed using a **keyed hash (HMAC)**, stable per deployment (not a raw SHA of the path), to reduce dictionary-attack risk on predictable paths.
- Never include credentials, raw SMB paths, raw S3 object keys, or internal URLs in logs, API responses, or artifacts.

### Process Patterns

**Secrets (provider-agnostic)**
- Secret material is never stored/returned/logged.
- MountProvider secrets (SMB v1 fields: `password_secret_path`, `password_secret_ref`, precedence path > ref) define the pattern; other providers must follow the same refs-only approach.

**Loading states (frontend)**
- No infinite loading: long-running operations must be time-bounded and degrade to “still working / retry / contact admin / runbook link” without losing context.
- “No dead actions”: hide by default; show disabled only for discoverability with “why + next action”.

**E2E / determinism**
- Product requirement: Chrome/Edge/Firefox compatibility (last 2 majors); WebKit/Safari is not a v1 requirement.
- CI gating pragmatism: 1 reference browser blocking; others non-blocking scheduled with quarantine policy.

**Dependency & security update policy**
- Dependency updates are handled via Renovate (configured in `renovate.json`). Do not add Dependabot version-bump PRs/config (e.g., `dependabot.yml`) to avoid duplication.
- Security monitoring relies on GitHub Dependabot Alerts (no auto update PRs).

### Enforcement Guidelines

**MUST (v1):**
- No-leak allow-listed evidence everywhere, and **no stack traces on public share-link endpoints**.
- Deterministic ordering + ordering **not client-controlled** unless an explicit allowlist is introduced.
- Strict mirror boundaries: BMAD local artifacts/registry are the source of truth; GitHub fork issues/PRs are mirror only.

**Guidelines (v1):**
- All other patterns in this section are expected defaults unless explicitly overridden by a documented architecture decision.

**Pattern Enforcement:**
- Validate via code review + pytest/jest/playwright + deterministic artifacts under `_bmad-output/implementation-artifacts/`.
- Any deviation must be documented as a deliberate decision (architecture decision entry) before implementation proceeds.

## Project Structure & Boundaries

### Complete Project Directory Structure

#### Repository structure (checked-in, portable)

```text
drive/
├── CHANGELOG.md
├── compose.yaml
├── Dockerfile
├── Makefile
├── README.md
├── package.json
├── package-lock.json
├── renovate.json
├── playwright-mcp.config.json
├── bin/
├── docker/
│   ├── auth/realm.json
│   ├── files/
│   │   ├── development/etc/nginx/conf.d/default.conf
│   │   └── production/etc/nginx/conf.d/default.conf
│   └── onlyoffice/...
├── env.d/
│   └── development/
│       ├── common
│       ├── postgresql
│       ├── postgresql.e2e
│       └── kc_postgresql
├── docs/
│   ├── env.md
│   ├── entitlements.md
│   ├── resource_server.md
│   ├── metrics.md
│   ├── ds_proxy.md
│   ├── theming.md
│   ├── release.md
│   └── installation/
│       ├── README.md
│       └── kubernetes.md
├── src/
│   ├── backend/
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── drive/
│   │   ├── core/
│   │   │   ├── api/
│   │   │   ├── authentication/
│   │   │   ├── entitlements/
│   │   │   ├── external_api/
│   │   │   ├── storage/
│   │   │   ├── services/
│   │   │   ├── tasks/
│   │   │   ├── utils/
│   │   │   └── tests/
│   │   ├── wopi/
│   │   │   ├── services/
│   │   │   ├── tasks/
│   │   │   └── tests/
│   │   ├── e2e/
│   │   └── demo/
│   ├── frontend/
│   │   ├── package.json
│   │   ├── apps/
│   │   │   ├── drive/
│   │   │   ├── e2e/
│   │   │   └── sdk-consumer/
│   │   └── packages/sdk/
│   ├── helm/            # reference in v1 (no new guarantees/gates)
│   ├── mail/
│   └── nginx/
└── .github/workflows/...
```

#### BMAD artifacts (checked-in)

This repo keeps planning artifacts under `_bmad-output/` for context and traceability.

**Planned additive boundaries (to be created):**
- Backend MountProvider boundary: `src/backend/core/mounts/` (planned; single bounded package to avoid scattering mount logic)
  - `core/mounts/providers/` (SMB provider, future providers)
  - `core/mounts/config/` (static mount config schema + validation)
  - `core/mounts/secrets/` (refs-only secret resolver; deterministic precedence; bounded-time refresh)
  - `core/mounts/capabilities.py` (documented constants for capability keys)
  - `core/mounts/api/` (mount endpoints + serializers; integrates with existing DRF routing)
  - `core/mounts/tests/` (unit/integration tests; Samba integration tests when added)
- Backend diagnostics boundary (API-first payload): `src/backend/core/diagnostics/` (planned; stable payload + safe-evidence allow-listing)
- Docker-first runbooks (v1 scope): `docs/selfhost/` (planned; Docker/Nginx/TLS/backup/restore/upgrade runbooks)
- Frontend mounts feature boundary: `src/frontend/apps/drive/src/features/mounts/` (planned; mount UI feature module)

### Architectural Boundaries

**API Boundaries:**
- Internal API: `/api/v1.0/...` (Drive app + authenticated operations; DRF viewsets/actions).
- External API / resource-server: `/external_api/v1.0/...` (strict allowlist, disabled-by-default).
- WOPI: backend `src/backend/wopi/` owns endpoints, lock semantics (cache TTL), and tests.

**Component Boundaries:**
- Frontend (Next.js Drive app) is a renderer of backend capability/diagnostics payloads (no parallel diagnostics logic).
- MountProvider is a plugin-like boundary; all providers conform to the same capability contract and no-leak rules.
- Secret resolution is centralized (refs-only; never store/return/log secret material; rotation w/out restart must-have for mounts and S3 creds).

**Data Boundaries:**
- Canonical mount identity: `(mount_id, normalized_path)`.
- Public share-link errors must never reflect any path or SMB info (generic no-leak responses).
- `path_hash` is diagnostics-only and must use a keyed hash (HMAC), stable per deployment.

### Requirements to Structure Mapping

**Storage axis (MountProvider + SMB v1):**
- MountProvider interface/capabilities/config/secrets/API/tests: `src/backend/core/mounts/` (planned)
- Frontend mounts UX: `src/frontend/apps/drive/src/features/mounts/` (planned)
- E2E mount flows: `src/frontend/apps/e2e/__tests__/...`

**WOPI axis:**
- WOPI backend: `src/backend/wopi/`
- WOPI UI: `src/frontend/apps/drive/src/features/ui/preview/wopi/`
- WOPI “enabled & healthy” gating signals: diagnostics payload (planned) + capability-driven UI states

**Packaging axis (Docker-first v1):**
- Edge contract templates: `docker/files/{development,production}/etc/nginx/conf.d/default.conf`
- Docker-first runbooks: `docs/selfhost/` (planned; v1 scope)

**Automation axis (historical / optional):**
- Some planning docs mention strict mirror, gate IDs, and deterministic artifacts. These are optional and are not required for day-to-day development in this fork.

### Integration Points

- BYO OIDC IdP ↔ backend auth (`mozilla-django-oidc`)
- BYO reverse proxy ↔ edge contract (Nginx reference) ↔ backend media-auth ↔ S3
- S3-compatible storage (SeaweedFS baseline v1) ↔ backend + edge proxy
- SMB server ↔ backend MountProvider (gateway model; planned)
- Redis ↔ Django cache (WOPI locks + caching)
- Postgres ↔ Django ORM + migrations

### Test Organization

- Backend tests: `src/backend/core/tests/`, `src/backend/wopi/tests/` (+ mount tests under `src/backend/core/mounts/tests/` planned).
- Frontend unit tests: `src/frontend/apps/drive` (Jest).
- E2E: `src/frontend/apps/e2e` (Playwright; multi-browser runnable; CI gating uses one reference browser, others scheduled non-blocking).

### Development Workflow Integration

- Dev bootstrap (DEV-only Makefile): `make bootstrap` / `make run` / Makefile E2E targets (as defined in repo).
- Deterministic artifacts: `_bmad-output/implementation-artifacts/` (no-leak; text scanning limited to `_bmad-output/**`).

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- The chosen stack is internally consistent and anchored to repo contracts: Django/DRF on Python `~=3.13.0` (`django<6.0.0`, `mozilla-django-oidc<5.0.0`, `drf-standardized-errors`, `drf-spectacular`) and Next.js `15.4.9` / React `19.2.0` on Node `>=22 <25`.
- S3-first + proxy/media contract + CT-S3 audience-aware diagnostics align with the no-leak and determinism requirements (audience codes carried separately from `failure_class`).
- MountProvider boundary is additive and provider-agnostic, matching the brownfield constraint (no re-scaffold) while keeping churn low as a delivery-system constraint.

**Pattern Consistency:**
- Naming and error-format rules are coherent across backend/UI/artifacts (capability keys as constants, stable error format + `failure_class` + `next_action_hint`, and explicit no-leak evidence allow-list).
- Secrets policy is consistent: refs-only (env/file), deterministic precedence, and bounded-time refresh for mounts (and S3 creds), without leaking secret material in logs/APIs/artifacts.

**Structure Alignment:**
- The portable repo structure vs BMAD/host workspace split avoids agent confusion and matches strict-mirror process boundaries.
- Planned additive boundaries (`core/mounts/`, `core/diagnostics/`, `docs/selfhost/`, frontend mounts feature) align with how work will be delivered without implying those directories already exist.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
- Identity, access and policy are covered via BYO OIDC IdP (v1 stays on `mozilla-django-oidc`) and entitlements-driven authorization/capability gating.
- Core file experience is covered with S3-first flows, proxy/media contract constraints, and actionable diagnostics (API-first payload) without leaking sensitive data.
- MountProvider + SMB mount v1 is covered by the planned bounded package, canonical identifiers `(mount_id, normalized_path)`, capability-driven actions, streaming transfers, and public share-link 404/410 semantics with strict no-leak errors.
- WOPI intent is covered as capability-driven (prerequisites + enabled/healthy) for eligible files across S3 and mounts, with locks via Redis/Django cache and strict “enabled & healthy” reachability requirement (without prescribing implementation).
- Fork-only delivery constraints and strict mirror requirements are covered (BMAD artifacts as source of truth; fork PRs/issues as mirror only; upstream snapshot read-only).

**Non-Functional Requirements Coverage:**
- Streaming/no buffering rules are captured for backend-mediated transfers (mounts + WOPI save pipeline).
- Determinism is captured via stable ordering, stable gate IDs/artifacts, and stable `failure_class` taxonomy.
- Security/no-leak is captured as a cross-cutting MUST, including “never stack traces” on public share-link endpoints and safe evidence allow-listing.
- Packaging and operability are covered with Docker-first v1 baseline and explicit “K8s reference only” stance for v1.

### Implementation Readiness Validation ✅

**Decision Completeness:**
- High-risk drift points (audience codes, `failure_class` schema, MountProvider vocabulary/capabilities, secrets rotation, strict mirror boundaries) are explicitly fixed as constants/policies.

**Structure Completeness:**
- The repo tree reflects checked-in structure plus clearly marked planned boundaries, reducing navigation ambiguity for agents.

**Pattern Completeness:**
- No-leak, determinism, capability-gating, and error-format rules are defined at a level that supports consistent implementation across backend, runners, and UI.

### Gap Analysis Results

**Critical gaps (blocking):** None identified.

**Important gaps (should be specified early in implementation to avoid rework):**
- MountProvider contract details: config schema validation, secret resolver refresh strategy (polling/watch + TTL), and provider capability evaluation paths for `mount.upload` / `mount.preview` / `mount.wopi` / `mount.share_link`.
- Diagnostics payload spec: finalize the stable schema (API-first) consumed by Drive UI and future Suite Control Panel, including safe evidence allow-lists and `next_action_hint` cataloging.
- Deterministic ordering: finalize and document the exact ordering implementation (folder-first + casefold + unique stable tie-breaker) and ensure it is identical across backends and UI.
- External API allowlist: define and document the exact route/action allowlist exposed under `/external_api/v1.0/...` (disabled-by-default by default).

**Nice-to-have gaps (future enhancements):**
- Kubernetes packaging hardening (charts/values/cert-manager/ingress contracts) as a v2+ epic (reference files remain “as-is” for v1).
- Multi-browser CI gating expansion once flakiness is under control (keep WebKit best-effort / non-blocking if present).

### Validation Issues Addressed

- Corrected ambiguity sources and anti-drift rules (failure class schema, audience constants, share-link no-leak behavior, deterministic ordering guardrails).
- Corrected repository vs BMAD workspace structure description to avoid agents assuming local host paths exist.
- Clarified dependency update strategy (Renovate for updates; Dependabot Alerts for monitoring only).

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Clear, constant-driven contracts at known drift points (audience, capabilities, errors, ordering, secrets)
- Strong security/no-leak stance with deterministic diagnostics and actionable next steps
- Delivery-system constraints prevent automation from leaking into upstream or diverging from strict mirror

**Areas for Future Enhancement:**
- Expand provider profiles/gates and strengthen K8s packaging beyond “reference-only”
- Promote additional E2E browsers to blocking gates once stable

### Implementation Handoff

**AI Agent Guidelines:**
- Follow the MUST rules in “Enforcement Guidelines” without exception unless a new architecture decision explicitly overrides them.
- Treat `failure_class`, audience codes, and capability keys as constants; do not invent new strings ad-hoc.
- Enforce no-leak on all public surfaces and artifacts; keep evidence allow-listed.
- Keep new subsystems bounded (MountProvider, diagnostics) to avoid scattering.

**First Implementation Priority:**
- Establish the planned bounded packages (`core/mounts/`, `core/diagnostics/`) with contract-first constants (capabilities, audiences, error shapes) and tests, then wire minimal end-to-end flows behind capability gating.
