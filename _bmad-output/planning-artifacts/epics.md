---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# drive - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for drive, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Users can authenticate via an external OIDC Identity Provider (bring-your-own).
FR2: Operators can use `DRIVE_PUBLIC_URL` as the default basis for public-facing redirect/origin configuration, and can explicitly configure additional allowed redirect hosts/URIs when required by their IdP setup.
FR3: The system can enforce application access and capability policies via an entitlements mechanism (e.g., can_access, can_upload).
FR4: Integrators can enable Drive as a Resource Server and call External API routes permitted by configuration.
FR5: Operators can restrict which External API endpoints/actions are exposed.
FR6: Authenticated users can browse their workspaces and navigate folders.
FR7: Users can create folders.
FR8: Users can upload files to S3-backed storage via a browser-compatible upload flow.
FR9: Users can download files.
FR10: Users can preview supported files through the standard preview flow.
FR11: Users can recover from common operational failures with clear, actionable feedback and safe diagnostics (no secrets), including at least: interrupted uploads, expired upload authorization, temporary storage unavailability, upload denied by policy/entitlements, and proxy/media access authorization failures.
FR12: Operators can configure upload part sizing/chunk sizing for large uploads (S3 multipart and MountProvider uploads where applicable), with documented defaults and limits, **per-backend and per-mount where applicable**.
FR13: Operators can configure MountProvider-based mounts with a stable `mount_id`, display name, provider type, and provider-specific non-secret connection parameters.
FR14: Operators can enable/disable mounts without changing existing S3-backed behaviors.
FR15: Users can discover available mounts and their capabilities via an API and a UI entry point.
FR16: Users can browse a mount (list directories and view file/folder metadata) with deterministic ordering and pagination/limits.
FR17: Users can download a mount file via backend-mediated streaming.
FR18: Users can upload to a mount via backend-mediated streaming (large-file capable).
FR19: Users can preview mount files when supported, with explicit capability-driven behavior when not supported.
FR20: The system can enforce mount capability gating so unavailable actions are hidden/disabled (no dead buttons).
FR21: The system can support at least one MountProvider implementation in v1 (SMB as the initial provider) without rewriting the S3-first core behavior.
FR22: Operators can configure an SMB mount with explicit connection parameters including (at minimum): `server` (host/IP), `share`, `port` (defaultable), `domain/workgroup` (optional), `username`, and a secret reference for the password (e.g., `password_secret_ref` and/or `password_secret_path`, reference only—not the secret value); plus optional SMB-specific settings such as `base_path` (share subpath) and connection timeouts.
FR23: Operators can reference secrets from mount configuration (e.g., `password_secret_ref`) rather than storing secret material in the database.
FR24: The system can resolve mount secrets at runtime from operator-managed secret sources (e.g., env/file-backed secrets) without exposing secret values in APIs, logs, or generated artifacts.
FR25: The system can enforce that secret values are never returned via any API; secret fields are reference-only (or write-only if an admin API/UI exists).
FR26: If both secret reference mechanisms are supported (e.g., secret ref and secret path), the system can guarantee deterministic resolution precedence and document it.
FR27: The system can support secret rotation without restarting the backend: when the referenced secret value changes, subsequent mount operations use the updated credentials within a bounded, operator-configurable time (at latest on the next new connection/session).
FR28: The system can ensure mount connection/session reuse is safe across secret rotation and does not reuse stale credentials after a secret change; in-flight failures must not leak secret material.
FR29: Users can create share links for S3-backed files and folders according to Drive’s sharing model.
FR30: Users can create share links for MountProvider-backed resources identified by `(mount_id, path)`, with the explicit accepted constraint that links may break if the underlying target is renamed/moved/deleted out-of-band.
FR31: Share link access can be enforced by token, without requiring an authenticated session (when configured as public).
FR32: For MountProvider share links, the system can enforce deterministic and clean error semantics (no stacktraces):
FR33: The system can provide clear behavior when mount targets change out-of-band (no silent failures).
FR34: The system can expose WOPI actions only when enabled by explicit capability/prerequisites per storage backend (core S3 vs MountProvider-based mounts).
FR35: If core S3 backend prerequisites (e.g., bucket versioning) are not met, the system can disable WOPI for that backend and provide operator-facing guidance (message + documentation reference).
FR36: For MountProvider-based WOPI, the system can enforce an application-level version string and lock semantics (TTL, release, conflict handling).
FR37: Users can launch WOPI editing for eligible files through a reverse-proxy-compatible flow.
FR38: The system can enforce WOPI host allowlist inputs derived from `DRIVE_PUBLIC_URL`.
FR39: The system can save WOPI edits back to the underlying storage backend through the supported write pipeline.
FR40: Operators can set a canonical public base URL (`DRIVE_PUBLIC_URL`) and derive public-facing URLs consistently from it.
FR41: Operators can deploy Drive behind a user-managed reverse proxy, using an Nginx reference configuration or an equivalent proxy-agnostic contract.
FR42: The system can support the media access flow via an edge proxy auth subrequest pattern (e.g., `/media` auth subrequest) and preserve SigV4 headers returned by the media-auth endpoint when proxying media requests to S3 (e.g., `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`, and optionally `X-Amz-Security-Token`).
FR43: Operators can follow documented procedures for backup/restore (DB + object storage + any locally-managed dev/test IdP fixtures if applicable) and validate with a post-restore smoke checklist.
FR44: Operators can follow documented upgrade/rollback procedures and validate with a smoke checklist.
FR45: Developers/CI can run Drive-integrated S3 contract tests with explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER).
FR46: Contract test reports can capture safe evidence (status codes, request_id, hashes) without leaking credentials or sensitive paths/keys.
FR47: The project can support a baseline S3-compatible provider profile in v1 (SeaweedFS as blocking profile) and encode expectations as repeatable tests and runbook checks.
FR48: Developers/CI can execute checks via stable `gate_id`s (resolved to existing Makefile targets/commands by a gates runner).
FR49: Each gate execution can produce deterministic artifacts (machine-readable + human-readable) under `_bmad-output/implementation-artifacts/`.
FR50: The system can classify failures with stable `failure_class` values and provide a `next_action_hint`.
FR51: The project can compute a registry fingerprint (B+) from the canonical subset and embed it into issue/PR bodies.
FR52: The system can detect and block strict-mirror drift (missing/mismatched fingerprints or template divergence).
FR53: The system can enforce no-leak as a global requirement for APIs/logs/artifacts (not limited to scanned outputs).
FR54: The system can limit automated scanning scope to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) to reduce false positives.

### NonFunctional Requirements

NFR1: Backend-mediated transfers (MountProvider downloads/uploads, WOPI save flows) shall be streaming and shall not require buffering entire file contents in memory, across v1-supported file sizes. **Verified via:** `backend.tests` + `mounts.integration.smb` (streaming contract) and retained failure artifacts.
NFR2: Default upload size limits and large-upload behaviors (including multipart/part sizing) shall be documented (including defaults and min/max limits) and operator-configurable per backend and per mount where applicable. **Verified via:** `backend.tests` (config validation) + documented runbook checks.
NFR3: The system shall provide deterministic, actionable failure reporting for automated gates and contract tests (stable `failure_class` + `next_action_hint`) and include both fields in reproducible artifacts for every failing gate execution. **Verified via:** gates runner artifact schema checks in `backend.tests` and CI.
NFR4: Backup/restore and upgrade/rollback procedures shall be documented and include a deterministic post-action smoke checklist (login, browse, upload, and media access via `media-auth`) executed after restore/upgrade actions. **Verified via:** runbook execution + `e2e.chrome` smoke flow and/or scripted smoke checklist artifacts.
NFR5: No-leak is enforced globally: secrets, credentials, and sensitive paths/keys shall not appear in API responses, logs, or generated artifacts (including on connection/auth failures). **Verified via:** CI and gates runner no-leak scanning for `_bmad-output/**` text artifacts plus targeted tests for redaction/no-logging.
NFR6: Automated no-leak scanning shall be limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) to reduce false positives while preserving the global no-leak requirement, during CI execution and during local gates runner execution. **Verified via:** gates runner scan configuration (scope/type) executed in CI.
NFR7: Production deployments shall support HTTPS for the public entry point (`DRIVE_PUBLIC_URL`) with no mixed TLS modes. **Verified via:** deployment docs + smoke checklist runbook and proxy configuration checks.
NFR8: The product shall maintain WCAG 2.1 AA compatibility with a “no regressions” policy across v1 work (including mounts and WOPI entry points when enabled) and must not introduce new serious/critical violations in the automated accessibility checks for the scoped flows. **Verified via:** `e2e.chrome` + automated accessibility checks (axe-based) with retained artifacts.
NFR9: The system shall remain compatible with a bring-your-own external OIDC IdP, including operator-configurable redirect allowances when required by the IdP configuration, and must support a successful login smoke flow when configured. **Verified via:** `backend.tests` (config validation) + end-to-end login smoke in `e2e.chrome`.
NFR10: Reverse-proxy behavior shall be proxy-agnostic by contract (Nginx as a reference), including the `/media` auth subrequest contract and SigV4 header propagation (including optional STS token) for media proxying. **Verified via:** `s3.contracts.seaweedfs` + documented proxy contract smoke checklist.

### Additional Requirements

- Brownfield constraint: do not re-scaffold with a new starter template; implement within the existing Django/DRF + Next.js repository structure.
- Preserve the `/media` edge contract: auth subrequest + SigV4 header propagation (including optional STS token) for media proxying.
- `DRIVE_PUBLIC_URL` is the single source of truth for public-facing host derivations (redirects, share links, WOPI allowlist, CORS origins), with explicit operator-configurable exceptions when required.
- Audience-aware storage correctness model is required: INTERNAL/PROXY vs EXTERNAL/BROWSER audiences, with stable constant codes and consistent semantics across CT-S3, diagnostics payloads, docs, and UI.
- S3 provider profiles (v1): SeaweedFS S3 gateway is the blocking baseline for Docker/self-host; ds-proxy is non-blocking/quarantine; Ceph RGW is a future Kubernetes profile to adopt before production migrations.
- Sprint 0 storage baseline: the default self-host/dev/CI baseline must be aligned to SeaweedFS (not MinIO). Any MinIO compose fixtures may remain, but must not be treated as the v1 baseline for blocking guarantees/gates/runbooks.
- Secrets are refs-only: never store/return/log secret material; support runtime secret resolution and rotation without restart (must-have for MountProvider secrets and S3 credentials).
- MountProvider SMB secret fields define the pattern: support `password_secret_path` and `password_secret_ref` with deterministic precedence (path > ref).
- Public share-link endpoints must never reflect any path (including normalized mount paths) or SMB connection details in errors; return clean, no-leak responses (no stack traces) and prefer `failure_class` + `next_action_hint`.
- If a diagnostics-only `path_hash` is used for safe evidence, it must be a keyed hash (HMAC), stable per deployment; do not replace normalized paths in authenticated browse APIs.
- Gate IDs are stable strings (e.g., `backend.tests`, `mounts.integration.smb`, `s3.contracts.seaweedfs`) and should not be documented as raw shell commands inside requirements/acceptance criteria.
- New backend behavior must ship with pytest tests (unit/integration where applicable) following existing test layout conventions.
- Desktop-first posture; responsive “no regressions”: mobile/tablet remain usable for basic actions (browse, download, open share link). Mobile upload is best-effort (not guaranteed for v1).
- Long-running operations (upload, preview, WOPI) must be time-bounded: no infinite spinners; degrade to an explicit “still working / retry / contact admin / runbook link” state without losing context.
- Capability-driven UI: avoid dead actions; when a feature is disabled/unavailable, clearly explain “why” and the “next action”.
- Context-preserving navigation: after actions (upload/rename/share/WOPI/preview exit), return to the same folder/selection/view and preserve scroll position when feasible.
- Upload feedback must be explicit and robust: visible queue, per-file progress, actionable errors, and upload status continuity even when navigating across folders.
- Accessibility baseline: WCAG 2.1 AA “no regressions”, with targeted improvements on critical flows (Explorer tree/list keyboard navigation; modals focus management; accessible upload feedback).
- Modal accessibility: focus enters the modal, is trapped, and returns to the launcher on close; correct ARIA labels/roles; predictable close behavior.
- Visible focus indicators everywhere; do not rely on color only to convey status; `aria-live` announcements must be meaningful and rate-limited (prefer milestones).
- No-leak UX: never show raw error objects, stack traces, internal URLs/paths/keys/credentials in UI surfaces.
- Diagnostics UX must be proxy-agnostic: describe required edge contracts, not a specific proxy; expose audience model + `failure_class` + safe evidence (allow-list) and always provide a next action.
- Reuse existing UI kit tokens, spacing/typography patterns, and breakpoints/responsive helpers; avoid introducing a new Settings/Admin area in v1 (attach support/diagnostics to existing Explorer patterns such as right panel/modals).
- Mount configuration and mount secrets are operator-managed via env/files (refs-only); **no in-app admin UI** for mount secret validate/refresh/status in v1 (admin UI is a separate project).
- WOPI v1 focus: Collabora-only. OnlyOffice may remain present as an existing fixture, but v1 work must not remove it, add it, or expand it; do not introduce gates or requirements that depend on OnlyOffice.
- Docker-first v1: Kubernetes remains “as-is reference” only; no Kubernetes improvements or Kubernetes-specific gates in v1 scope.
- Dependency automation policy: use Renovate for version bump PRs; use Dependabot for security alerts only (no Dependabot PRs).
- Audience codes/constants must be exactly `INTERNAL_PROXY` and `EXTERNAL_BROWSER` everywhere (CT-S3, diagnostics payloads, docs, UI); do not introduce alternative codes.
- MountProvider capability keys are documented constants: `mount.upload`, `mount.preview`, `mount.wopi`, `mount.share_link`.
- MountProvider virtual entry identity is `(mount_id, normalized_path)`; any diagnostics-only `path_hash` must be HMAC (keyed hash), stable per deployment.
- No-leak evidence policy: safe evidence is allow-listed (explicit allow-list), not “redact after the fact”; public share-link errors must never reflect path/SMB info, must return `404`/`410` semantics, and must never include stack traces.
- Optional: keep GitHub issues/PRs aligned with `_bmad-output/**` planning artifacts for collaboration, but do not assume automated strict-mirror enforcement.

### FR Coverage Map

FR1: Epic 3 - BYO OIDC authentication
FR2: Epic 1 - `DRIVE_PUBLIC_URL` basis + explicit redirect allowlists
FR3: Epic 3 - entitlements-driven access/capabilities
FR4: Epic 3 - resource server enablement for external API routes
FR5: Epic 3 - restrict exposed external API endpoints/actions
FR6: Epic 4 - browse workspaces/folders
FR7: Epic 4 - create folders
FR8: Epic 4 - S3 browser upload flow
FR9: Epic 4 - download files
FR10: Epic 4 - preview supported files
FR11: Epic 5 - actionable recovery from operational failures (no-leak)
FR12: Epic 4 - configurable chunk/part sizing per backend/mount
FR13: Epic 7 - configure mounts (`mount_id`, provider, params)
FR14: Epic 7 - enable/disable mounts without changing S3 behavior
FR15: Epic 7 - discover mounts + capabilities (API + UI entry)
FR16: Epic 7 - browse mount with deterministic ordering + pagination
FR17: Epic 9 - download mount file via backend streaming
FR18: Epic 9 - upload to mount via backend streaming (large-file capable)
FR19: Epic 9 - preview mount files when supported (capability-driven)
FR20: Epic 7 - capability gating (no dead actions)
FR21: Epic 7 - MountProvider boundary supports SMB v1 without rewriting S3 core
FR22: Epic 9 - SMB mount configuration parameters
FR23: Epic 8 - mount secrets are references (no secret material in DB)
FR24: Epic 8 - runtime secret resolution from operator-managed sources (no leak)
FR25: Epic 8 - enforce secrets never returned via API
FR26: Epic 8 - deterministic secret resolution precedence
FR27: Epic 8 - secret rotation without restart (bounded time)
FR28: Epic 8 - safe session reuse across rotation; no secret leaks on failures
FR29: Epic 6 - share links for S3 files/folders
FR30: Epic 7 - share links for MountProvider resources `(mount_id, path)`
FR31: Epic 6 & 7 - token-enforced access without authenticated session (when public)
FR32: Epic 7 - deterministic MountProvider share-link error semantics (no stacktraces)
FR33: Epic 7 - explicit behavior for out-of-band mount target changes
FR34: Epic 10 - expose WOPI actions only when capability/prereqs met per backend
FR35: Epic 10 - disable WOPI on S3 prereq failure; operator guidance
FR36: Epic 10 - mount WOPI version string + lock semantics (TTL/release/conflicts)
FR37: Epic 10 - launch WOPI editing via reverse-proxy-compatible flow
FR38: Epic 10 - WOPI host allowlist derived from `DRIVE_PUBLIC_URL`
FR39: Epic 10 - save WOPI edits back to underlying storage backend
FR40: Epic 1 - canonical public base URL derivations from `DRIVE_PUBLIC_URL`
FR41: Epic 2 - deploy behind user-managed reverse proxy (Nginx reference/contract)
FR42: Epic 2 - `/media` auth subrequest + SigV4 header propagation via edge proxy
FR43: Epic 2 - documented backup/restore + post-restore smoke checklist
FR44: Epic 2 - documented upgrade/rollback + smoke checklist
FR45: Epic 11 - run Drive-integrated S3 contract tests with explicit audiences
FR46: Epic 11 - CT-S3 reports capture safe evidence without leaks
FR47: Epic 11 - SeaweedFS blocking baseline profile encoded as repeatable tests/checks
FR48: Epic 12 - stable `gate_id`s executed via gates runner
FR49: Epic 12 - deterministic artifacts under `_bmad-output/implementation-artifacts/`
FR50: Epic 12 - stable `failure_class` + `next_action_hint`
FR51: Epic 12 - registry fingerprint (B+) embedded in issue/PR bodies
FR52: Epic 12 - detect/block strict-mirror drift
FR53: Epic 12 - enforce no-leak globally for APIs/logs/artifacts
FR54: Epic 12 - limit automated scanning scope to `_bmad-output/**` text artifacts

## Epic List

### Epic 1: Canonical Public URL & Public Surface Configuration
Operators can define `DRIVE_PUBLIC_URL` as the single source of truth for public-facing host derivations, including OIDC redirect allowances when required.
**FRs covered:** FR2, FR40

### Epic 2: Docker-first Self-host Ops + Reverse Proxy Media Contract (K8s reference-only)
Operators can deploy Drive **Docker-first (v1)** behind a user-managed reverse proxy (proxy-agnostic contract, Nginx reference), preserve the `/media` auth_request + SigV4 propagation flow, and execute backup/restore + upgrade/rollback runbooks with smoke checks; Kubernetes/Helm remain reference-only (as-is) in v1.
**FRs covered:** FR41, FR42, FR43, FR44

### Epic 3: Identity, Entitlements & External API Policy
Users can authenticate via a BYO external OIDC Identity Provider; operators can enforce entitlements and control which external API endpoints/actions are exposed; integrators can enable Drive as a Resource Server for permitted external API routes.
**FRs covered:** FR1, FR3, FR4, FR5

### Epic 4: Core S3 File Experience (Browse → Upload → Preview → Download)
End users can browse workspaces, create folders, upload/download files, and preview supported files on S3-backed storage; operators can configure chunk/part sizing per backend and per mount where applicable.
**FRs covered:** FR6, FR7, FR8, FR9, FR10, FR12

### Epic 5: Resilience & Messaging Patterns (Cross-cutting)
Establish cross-cutting patterns (time-bounded long-running states, actionable errors, no-leak messaging + safe evidence) reused across end-user flows (S3, share links, mounts/SMB, WOPI) and operator-first surfaces (Diagnostics right panel), rather than a UI-only silo.
**FRs covered:** FR11

### Epic 6: Share Links (S3) with Public Token Access
Users can create share links for S3 items; public access is token-based and works without an authenticated session when configured as public.
**FRs covered:** FR29, FR31

### Epic 7: MountProvider Framework: Contract-level Browse/Discover + Capability Gating
Framework epic (contract-level): configure mounts, enable/disable without impacting S3, discover mounts/capabilities, browse with deterministic ordering/pagination, enforce capability gating (no dead actions), and support MountProvider share links with deterministic semantics when capability is enabled.
Source of truth for constants/naming: `_bmad-output/planning-artifacts/architecture.md` → “Implementation Patterns & Consistency Rules” (capability keys `mount.upload|mount.preview|mount.wopi|mount.share_link`, virtual entry `(mount_id, normalized_path)`, diagnostics `path_hash` as HMAC, audience constants).
**FRs covered:** FR13, FR14, FR15, FR16, FR20, FR21, FR30, FR31, FR32, FR33

### Epic 8: Mount Secrets: Refs-only Resolution + Hot Rotation
Operators can reference secrets (ref/path) in mount configuration; the system resolves secrets at runtime without leaks, enforces refs-only semantics, deterministic precedence, and rotation without restart; session reuse across rotation is safe.
**FRs covered:** FR23, FR24, FR25, FR26, FR27, FR28

### Epic 9: SMB Mount v1 Provider: Streaming Upload/Download/Preview (Implementation-level)
Provider epic (implementation-level): SMB-specific configuration + backend-mediated streaming download/upload and preview where supported, implemented on top of the Epic 7 framework contracts; share links are handled via Epics 6 (S3) and 7 (MountProvider), and WOPI via Epic 10.
**FRs covered:** FR22, FR17, FR18, FR19

### Epic 10: WOPI/Collabora Editing (Capability-driven, Enabled & Healthy)
WOPI actions appear only when prerequisites are met per backend; if S3 prerequisites (e.g., bucket versioning) are not met, WOPI is disabled with operator guidance; MountProvider WOPI uses app-level version string and lock semantics; users can launch WOPI editing via reverse-proxy-compatible flow; host allowlist derives from `DRIVE_PUBLIC_URL`; edits save back through the supported write pipeline.
**FRs covered:** FR34, FR35, FR36, FR37, FR38, FR39

### Epic 11: Storage Correctness Proof: CT-S3 (SeaweedFS Baseline, Audience-aware)
Developers/CI can run Drive-integrated S3 contract tests with explicit audiences; reports capture safe evidence without leaks; v1 supports SeaweedFS as the blocking baseline provider profile encoded as repeatable tests and runbook checks.
**FRs covered:** FR45, FR46, FR47

### Epic 12: Deterministic Delivery System: Gates, Artifacts, failure_class, Strict Mirror
Developers/CI can run stable `gate_id`s via a gates runner, producing deterministic artifacts; failures are classified with stable `failure_class` values and a `next_action_hint`; registry fingerprint (B+) is embedded and drift is blocked; no-leak is enforced with scanning scope limited to `_bmad-output/**` text artifacts. This epic wires CT-S3 gates that run the suite delivered by Epic 11.
**FRs covered:** FR48, FR49, FR50, FR51, FR52, FR53, FR54

## Epic 1: Canonical Public URL & Public Surface Configuration

Operators can define `DRIVE_PUBLIC_URL` as the single source of truth for public-facing host derivations, including OIDC redirect allowances when required.

### Story 1.1: Canonical `DRIVE_PUBLIC_URL` validation and deterministic derivations

As an operator,
I want to configure a canonical public base URL (`DRIVE_PUBLIC_URL`) with strict validation and deterministic derivations,
So that all public-facing URLs/origins are consistent and misconfiguration fails early with actionable, no-leak errors.

**Acceptance Criteria:**

**Given** `DRIVE_PUBLIC_URL` is configured as an absolute URL with a scheme and host (and no query/fragment; path is empty or `/`)
**When** configuration preflight/validation runs
**Then** the system accepts it and uses a normalized base value for all derivations (e.g., no duplicate slashes).

**Given** `DRIVE_PUBLIC_URL` has a trailing slash (e.g., `https://drive.example.com/`)
**When** configuration preflight/validation runs
**Then** the system normalizes it (e.g., removes the trailing slash) so derived public URLs remain consistent.

**Given** `DRIVE_PUBLIC_URL` is invalid (missing host, includes query/fragment, includes an unexpected path, or otherwise not a valid canonical public base URL)
**When** configuration preflight/validation runs
**Then** the system fails early with a deterministic `failure_class` and a `next_action_hint`, without leaking secrets or sensitive paths.

**Given** `DRIVE_PUBLIC_URL` uses `http://` and the insecure dev override is not enabled
**When** configuration preflight/validation runs in a production deployment
**Then** the system rejects the configuration with a deterministic `failure_class` and a `next_action_hint` guiding to set `https://` or enable the dev-only override explicitly (e.g., `DRIVE_ALLOW_INSECURE_HTTP=true`).

### Story 1.2: Separate allowlists for redirect URIs vs origins/hosts (derived from `DRIVE_PUBLIC_URL`)

As an operator,
I want default allowed redirect/origin configuration to be derived from `DRIVE_PUBLIC_URL` and to support explicit additional allowlists split by purpose (redirect URIs vs origins/hosts),
So that I can integrate with IdPs requiring extra callbacks without creating a permissive or ambiguous configuration model.

**Acceptance Criteria:**

**Given** `DRIVE_PUBLIC_URL` is valid
**When** the system computes/validates allowlisted values
**Then** the canonical values derived from `DRIVE_PUBLIC_URL` are always included by default.

**Given** the operator configures additional allowed redirect URIs
**When** configuration preflight/validation runs
**Then** each entry is an absolute URI (scheme + host + path), is validated deterministically (no wildcards, no ambiguous parsing), is normalized/deduplicated, and in production requires `https://` unless the dev-only insecure override is explicitly enabled.

**Given** the operator configures additional allowed origins/hosts (for origin/CORS/host checks where applicable)
**When** configuration preflight/validation runs
**Then** each entry is validated deterministically (host-only or origin form as applicable), contains no wildcards, is normalized/deduplicated, and in production requires HTTPS origins where an origin is used unless the dev-only insecure override is explicitly enabled.

**Given** any allowlisted entry is invalid or unsafe for the current deployment mode
**When** configuration preflight/validation runs
**Then** the system fails early with deterministic `failure_class` + `next_action_hint`, without leaking secrets or sensitive paths.

## Epic 2: Docker-first Self-host Ops + Reverse Proxy Media Contract (K8s reference-only)

Operators can deploy Drive **Docker-first (v1)** behind a user-managed reverse proxy (proxy-agnostic contract, Nginx reference), preserve the `/media` auth_request + SigV4 propagation flow, and execute backup/restore + upgrade/rollback runbooks with smoke checks; Kubernetes/Helm remain reference-only (as-is) in v1.

### Story 2.1: Docker-first edge contract documentation + configuration validation + smoke checks

As an operator,
I want a Docker-first v1 deployment contract (proxy-agnostic) with documentation, configuration validation, and testable smoke checks,
So that I can deploy reliably behind my reverse proxy without drifting into Kubernetes/Helm scope in v1.

**Acceptance Criteria:**

**Given** v1 scope is Docker-first
**When** I read the self-host documentation/runbooks
**Then** Docker (single-machine / compose) is the baseline, and Kubernetes/Helm is explicitly “as-is reference-only” (no v1 improvements, no v1 K8s gates).

**Given** I deploy behind any reverse proxy (not necessarily Nginx)
**When** I consult the documentation
**Then** the required edge contract is described in proxy-agnostic terms (Nginx is a reference implementation only).

**Given** configuration preflight/validation runs
**When** it evaluates reverse-proxy/media-related configuration inputs
**Then** it validates the inputs deterministically (without attempting to “inspect” the actual proxy) and outputs an operator-facing checklist and/or guidance for verifying the edge contract in the deployed environment.

**Given** operator smoke checks are executed (via documented steps and/or optional smoke endpoint(s))
**When** they report results for media/S3 edge paths
**Then** the results reflect the audience model (`INTERNAL_PROXY` vs `EXTERNAL_BROWSER`) with safe evidence only (no-leak).

**Given** configuration is missing/unsafe/inconsistent for the current deployment mode
**When** preflight/validation runs
**Then** it fails early with deterministic `failure_class` + `next_action_hint`, and remains no-leak.

### Story 2.2: Nginx reference edge configuration (dev/prod aligned) for `/media` auth_request + SigV4 propagation

As an operator,
I want an Nginx reference configuration (dev and prod aligned) that implements the proxy-agnostic `/media` edge contract,
So that I can deploy Drive behind Nginx (or replicate the same behavior in another proxy) while preserving the media auth flow and SigV4 requirements.

**Acceptance Criteria:**

**Given** I use Nginx as my reverse proxy
**When** I apply the provided Nginx reference configuration/templates (dev + prod variants)
**Then** the `/media` routes follow the edge contract using an auth subrequest pattern to the backend media-auth endpoint.

**Given** the backend media-auth endpoint returns SigV4-related headers for the upstream storage request
**When** Nginx proxies the media request to S3
**Then** it forwards all required SigV4-related headers returned by media-auth (including `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`, and optionally `X-Amz-Security-Token`, plus any other required `x-amz-*` headers) without dropping or rewriting them.

**Given** dev and prod Nginx reference configs exist
**When** they are compared at the contract level
**Then** they remain aligned for media-auth subrequest behavior and header propagation (differences are limited to environment-specific concerns like TLS/hosts).

**Given** the reference Nginx config is used in production-like environments
**When** access/error logging is configured
**Then** SigV4 secrets are not logged or echoed (e.g., do not log `Authorization` or `X-Amz-Security-Token`), or the documentation provides an explicit, default-safe way to disable such logging.

**Given** an operator uses a different reverse proxy than Nginx
**When** they consult the documentation
**Then** the contract is described in proxy-agnostic terms, with Nginx as a reference implementation (no proxy lock-in).

### Story 2.3: TLS posture for public surfaces (prod HTTPS-only, dev override explicit, no mixed modes)

As an operator,
I want TLS rules that enforce HTTPS on all public surfaces in production, with an explicit dev-only override (centralized),
So that `DRIVE_PUBLIC_URL`-derived URLs are safe and consistent across redirects, share links, and WOPI.

**Acceptance Criteria:**

**Given** the deployment is production
**When** preflight/validation runs
**Then** `DRIVE_PUBLIC_URL` must be `https://…`, and any derived public surfaces (OIDC redirects/origins, share links, WOPI allowlist/launch URLs) are HTTPS-only; “no mixed TLS modes” is enforced for these public surfaces.

**Given** the deployment is development and the explicit insecure override is enabled (the same centralized override used by `DRIVE_PUBLIC_URL` validation)
**When** `DRIVE_PUBLIC_URL` uses `http://`
**Then** the configuration is accepted for dev, and guidance is explicit that production requires HTTPS.

**Given** derivation helpers generate public URLs from `DRIVE_PUBLIC_URL`
**When** they build derived public-surface URLs
**Then** they normalize slashes/trailing slash so URLs do not contain double slashes or inconsistent forms that would break redirects/CORS/WOPI.

**Given** any public-surface TLS rule is violated
**When** preflight/validation runs
**Then** it fails with deterministic `failure_class` + `next_action_hint`, and remains no-leak.

### Story 2.4: Docker-first backup/restore runbook + deterministic post-restore smoke checklist

As an operator,
I want a documented, Docker-first backup/restore procedure (DB + object storage + optional local dev/test IdP fixtures) with a deterministic post-restore smoke checklist,
So that I can recover from incidents and validate service health without ambiguity or leaks.

**Acceptance Criteria:**

**Given** I operate the Docker-first deployment
**When** I follow the backup runbook
**Then** it provides concrete, step-by-step instructions to back up:
- the database (metadata),
- the object storage (file blobs), preserving the required bucket layout/prefixes so restores do not silently break previews/WOPI/media flows,
- and any locally-managed dev/test IdP fixtures if applicable,
and explicitly states what is out of scope / not required (e.g., ephemeral caches), without leaking secrets.

**Given** I need to restore from backups
**When** I follow the restore runbook
**Then** it provides concrete, step-by-step instructions to restore DB + object storage into a consistent state for the Docker-first baseline, including prerequisites and safety notes (no-leak).

**Given** a restore completed
**When** I execute the post-restore smoke checklist
**Then** it includes at least these deterministic checks (with expected outcomes):
- login succeeds (with an operator-provided external OIDC IdP; Keycloak only if used as a dev fixture),
- browse a workspace/folder succeeds,
- open an existing file preview works or shows a clear, actionable state (no infinite loading; no-leak),
- upload succeeds (or fails with an actionable no-leak error),
- media access via the `/media` flow succeeds (or fails with an actionable no-leak error referencing the edge contract).
**And** if public share links are enabled for the environment, opening an existing share link works or shows a clear, actionable no-leak state.

### Story 2.5: Docker-first upgrade/rollback runbook + deterministic post-action smoke checklist

As an operator,
I want documented, Docker-first upgrade and rollback procedures with a deterministic post-action smoke checklist,
So that I can apply updates safely and recover quickly if something goes wrong, without ambiguity or leaks.

**Acceptance Criteria:**

**Given** I operate the Docker-first deployment
**When** I follow the upgrade runbook
**Then** it provides concrete, step-by-step instructions that make ordering explicit (e.g., pin/pull images → run migrations → restart services → smoke checks), plus prerequisites and safety notes, without leaking secrets.

**Given** an upgrade fails or must be reverted
**When** I follow the rollback runbook
**Then** it provides concrete, step-by-step instructions to rollback to a known-good state, including DB/object storage compatibility notes, and clarifies that rollback may require DB restore if migrations are not backward-compatible, without leaking secrets.

**Given** an upgrade or rollback completed
**When** I execute the post-action smoke checklist
**Then** it includes at least these deterministic checks (with expected outcomes):
- login succeeds (operator-provided external OIDC IdP; Keycloak only if used as a dev fixture),
- browse a workspace/folder succeeds,
- open an existing file preview works or shows a clear, actionable state (no infinite loading; no-leak),
- upload succeeds (or fails with an actionable no-leak error),
- media access via the `/media` flow succeeds (or fails with an actionable no-leak error referencing the edge contract).
**And** if public share links are enabled for the environment, opening an existing share link works or shows a clear, actionable no-leak state; if a mount-backed share link is tested, it respects the 404/410 semantics for MountProvider targets.

## Epic 3: Identity, Entitlements & External API Policy

Users can authenticate via a BYO external OIDC Identity Provider; operators can enforce entitlements and control which external API endpoints/actions are exposed; integrators can enable Drive as a Resource Server for permitted external API routes.

### Story 3.1: BYO OIDC authentication (refs-only secrets, config validation, smoke login proof)

As an operator,
I want Drive to support authentication via an operator-provided external OIDC Identity Provider with deterministic configuration validation and a smoke login flow,
So that the deployment is self-host reliable (no surprises) without coupling v1 to a specific IdP.

**Acceptance Criteria:**

**Given** the operator provides OIDC configuration inputs (issuer/discovery URL, client id, client secret ref via env var name and/or file path with deterministic precedence (file > env), and redirect/origin allowlists as defined in Epic 1 Story 1.2)
**When** configuration preflight/validation runs
**Then** it validates these inputs deterministically (no ambiguous parsing; no wildcards; production requires HTTPS unless the same centralized dev-only override used by Epic 1/2 TLS rules is explicitly enabled).
**And** secret material is never returned by APIs and is never logged (no-leak).
**And** failures return deterministic `failure_class` + `next_action_hint` (no-leak).

**Given** `DRIVE_PUBLIC_URL` is set
**When** redirect URIs are computed/validated
**Then** the default allowed redirect URIs match the canonical host derived from `DRIVE_PUBLIC_URL`.
**And** any additional redirect URIs require explicit configuration via the dedicated allowlist (Epic 1 Story 1.2), with deterministic validation and no wildcards.

**Given** production is configured with an operator-provided external OIDC IdP
**When** a user performs the login flow
**Then** authentication succeeds end-to-end and the user can prove session validity by fetching a minimal authenticated endpoint (e.g., `/api/v1.0/users/me/`) and/or browsing a workspace.

**Given** a dev fixture IdP is used
**When** documentation mentions Keycloak
**Then** it is explicitly described as dev/reference fixture only (BYO IdP remains the production posture).

### Story 3.2: Entitlements enforcement for access and uploads (API + UI gating)

As an operator,
I want application access and capability policies to be enforced via an entitlements backend (e.g., `can_access`, `can_upload`) and exposed to the UI via an authenticated API,
So that I can restrict access and uploads deterministically without leaking sensitive information.

**Acceptance Criteria:**

**Given** an `ENTITLEMENTS_BACKEND` is configured
**When** an authenticated user requests `GET /api/v1.0/entitlements/`
**Then** the response contains at least `can_access` and `can_upload` entries with a boolean `result` and an optional safe `message` (no secret material, no internal URLs/paths/keys).

**Given** the entitlements backend returns `can_access.result=false` for a user
**When** the user attempts to authenticate via OIDC
**Then** authentication is denied with a clean, no-leak error response that is actionable for operators (safe message), and no authenticated session is established.

**Given** the entitlements backend returns `can_upload.result=false` for a user
**When** the user attempts any upload-related operation
**Then** the operation is denied with a clean, no-leak error response using the safe entitlements message (or a safe default).
**And** if an upload created intermediate state (e.g., a pending file item), it is cleaned up deterministically to avoid orphaned items.

**Given** the UI fetches entitlements for the current user
**When** `can_upload.result=false`
**Then** upload actions are hidden/disabled without dead buttons, and the user sees an explicit, no-leak explanation (using the safe entitlements message when available).

### Story 3.3: External API allowlist for resources and actions (strict, no wildcards)

As an operator,
I want to enable the external API surface using a strict allowlist of resources and actions,
So that only explicitly permitted endpoints/actions are exposed (disabled-by-default, no wildcards).

**Acceptance Criteria:**

**Given** Resource Server mode is enabled
**When** a resource is not enabled in the external API configuration
**Then** its routes are not exposed under `/external_api/v1.0/...` (404).

**Given** a resource is enabled but an action is not allowlisted for that resource
**When** a client attempts the disallowed action
**Then** the request is rejected deterministically with a documented status code (v1: `403`), with a clean no-leak response.

**Given** a resource and action are allowlisted
**When** a client calls the corresponding external API endpoint
**Then** the request is permitted (subject to the normal authorization rules for that resource) and behaves consistently with the internal API contract.

**Given** the operator configures external API allowlists
**When** preflight/validation runs
**Then** configuration is validated deterministically and at action-level (resource + action names, not raw path prefixes), with no ambiguous parsing and no wildcards.
**And** failures include `failure_class` + `next_action_hint` (no-leak).

### Story 3.4: Resource Server mode (external API) is disabled-by-default and token-authenticated

As an integrator,
I want Drive to expose a dedicated external API surface as an OIDC Resource Server when explicitly enabled,
So that a suite service can call approved routes using bearer tokens without relying on the internal user session API.

**Acceptance Criteria:**

**Given** Resource Server mode is disabled
**When** a client calls any `/external_api/v1.0/...` endpoint
**Then** the server returns `404` (routes are not exposed).

**Given** Resource Server mode is enabled by explicit operator configuration
**When** a client calls a permitted `/external_api/v1.0/...` endpoint without a bearer token (or with an invalid/expired token)
**Then** the request is rejected with `401` and a clean, no-leak authentication error that remains generic for clients (do not leak introspection details).
**And** actionable details are reserved for operator-facing surfaces/diagnostics only (no-leak).

**Given** Resource Server mode is enabled and a bearer token is accepted as valid
**When** the token client identity/audience is not in the operator allowlist
**Then** the request is rejected deterministically with a documented status code (v1: `403`), and remains no-leak and generic for clients (do not expose token claims or rejection reasons).
**And** actionable details are reserved for operator-facing surfaces/diagnostics only (no-leak).

**Given** Resource Server mode is enabled
**When** bearer token validation is performed
**Then** it uses an introspection-based validation flow (not JWT-only), consistent with the configured OIDC OP endpoints.

**Given** Resource Server mode is enabled and a client secret is required for token introspection
**When** secret configuration is provided
**Then** it follows the refs-only pattern (env var ref and/or file path ref with deterministic precedence file > env), and secret material is never logged or returned by APIs (no-leak).

## Epic 4: Core S3 File Experience (Browse → Upload → Preview → Download)

End users can browse workspaces, create folders, upload/download files, and preview supported files on S3-backed storage; operators can configure upload chunk/part sizing per backend and per mount where applicable.

### Story 4.1: Browse workspaces and navigate folders (deterministic ordering + abilities contract)

As an authenticated end user,
I want to browse my workspaces and navigate folders,
So that I can find and access my files.

**Acceptance Criteria:**

**Given** the user is authenticated and has app access (`can_access=true`)
**When** the user lists their accessible workspaces and opens a workspace/folder
**Then** the API returns the expected folder contents and metadata needed for navigation.
**And** ordering and pagination are deterministic (API is the source of truth; no UI-side sorting assumptions).
**And** listed items include the user-relevant `abilities` required by the Explorer to render actions without dead buttons (e.g., `children_list`, `children_create`, `media_auth`, `upload_ended`, plus other relevant action flags as applicable to the view).

**Given** the user is not authenticated
**When** they try to browse workspaces or folders
**Then** the API rejects the request with a clean authentication error (no-leak).

### Story 4.2: Create folders in the explorer (capability-driven + clean validation)

As an authenticated end user,
I want to create folders inside a workspace/folder,
So that I can organize my content.

**Acceptance Criteria:**

**Given** the user is authenticated and `abilities.children_create=true` on the target folder
**When** the user creates a folder with a title under that parent
**Then** the folder is created successfully and appears when listing the parent’s children.

**Given** the user is authenticated but `abilities.children_create=false` on the target folder
**When** the user attempts to create a folder
**Then** the request is rejected deterministically with a clean, no-leak error response (no stacktrace).

**Given** the folder name/title is invalid (e.g., missing or conflicting at the same level)
**When** the API validates the request
**Then** it returns a clean validation error (no-leak, no stacktrace) with stable error codes/messages.

### Story 4.3: S3 presigned upload flow (create file → presigned PUT → upload-ended)

As an authenticated end user,
I want to upload files to S3-backed storage using a browser-compatible presigned flow,
So that I can add content reliably to my drive.

**Acceptance Criteria:**

**Given** the user is authenticated and `can_upload=true`
**When** the user creates a file entry and uploads the file using the returned presigned policy URL
**Then** the presigned URL is valid for the `EXTERNAL_BROWSER` audience and the browser can PUT the file to object storage.
**And** the backend upload finalization step (`upload-ended`) completes successfully.
**And** upload progress is visible and remains accessible while the user navigates to other folders/workspaces (no “lost upload” state), per Epic 5 resilience patterns.

**Given** `can_upload=false`
**When** the user attempts any upload-related operation
**Then** the operation is rejected with a clean, no-leak error (optionally using the safe entitlements message).
**And** any intermediate state is cleaned up deterministically (e.g., no orphaned “ready-looking” items in listings).

**Given** a presigned PUT upload fails before `upload-ended` is called
**When** the user refreshes the folder listing
**Then** the created item is not presented as ready (e.g., if it exists it remains `upload_state=pending`) and exposes no media/preview surfaces until finalized (concretely: no `url`/`url_preview`).
**And** any surfaced error follows Epic 5 patterns (actionable, no-leak, no infinite loading).

### Story 4.4: Download files via `/media` (edge contract, Range support)

As an authenticated end user,
I want to download files,
So that I can access my content outside the explorer.

**Acceptance Criteria:**

**Given** the user has access to a ready file (`upload_state != pending`)
**When** the file is retrieved/listed
**Then** the API exposes a download URL (`url`) pointing to the `/media/...` surface (not a raw S3 endpoint).

**Given** the user has access to the file
**When** the browser requests `GET {url}`
**Then** the file is served successfully via the edge contract (auth subrequest to `media-auth` + SigV4 header propagation), without requiring the browser to talk directly to S3.

**Given** the client issues an HTTP Range request to `{url}` (where applicable)
**When** the edge contract and storage backend support partial content
**Then** Range requests are supported deterministically (e.g., `206 Partial Content`), enabling large-file download/streaming behaviors.

**Given** the file is not ready (`upload_state=pending`) or the user is not allowed
**When** the browser requests `GET {url}` (or attempts to access `/media/...`)
**Then** access is denied with a clean, generic no-leak error for clients.
**And** operator-facing surfaces/diagnostics may provide actionable details via `failure_class` + safe evidence (no-leak).
**And** the UI follows Epic 5 patterns (actionable, no infinite loading).

### Story 4.5: Preview supported files via `/media/preview` (deterministic availability)

As an authenticated end user,
I want to preview supported files,
So that I can quickly inspect content without downloading.

**Acceptance Criteria:**

**Given** a file is ready and previewable by backend rules
**When** the file is retrieved/listed
**Then** the API exposes a preview URL (`url_preview`) pointing to `/media/preview/...`.
**And** preview availability is deterministic and derived from backend rules (not UI heuristics).

**Given** the user opens the preview
**When** the browser requests `GET {url_preview}`
**Then** the preview is served successfully via the edge contract (auth subrequest + SigV4 propagation).
**And** the UI remains time-bounded/actionable per Epic 5.

**Given** a file is ready but not previewable by backend rules
**When** the file is retrieved/listed
**Then** `url_preview` is absent/null.
**And** the UI shows an explicit “preview not available” state (distinct from “access denied”), with no dead actions and no-leak messaging.

### Story 4.6: Operator-configurable upload part/chunk sizing (documented defaults + deterministic validation)

As an operator,
I want upload part/chunk sizing for large uploads to be documented with defaults/limits and configurable per backend (and per mount where applicable),
So that large transfers remain reliable and tunable in real self-host environments.

**Acceptance Criteria:**

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

### Story 5.1: Time-bounded long-running operations (no infinite loading) with actionable fallback states

As an end user and operator,
I want long-running/fragile operations to be time-bounded and to degrade into explicit actionable states,
So that the UI never spins indefinitely and users/operators always know what to do next.

**Acceptance Criteria:**

**Given** a long-running operation is in progress (v1 mandatory surfaces: upload flow (queue/progress + finalize), preview open, WOPI launch, public share-link open (S3 + mounts), and Diagnostics refresh (right panel))
**When** the UI is waiting for completion
**Then** it uses time thresholds that are per-operation (and configurable with documented defaults) and follows a consistent state progression: `loading` → `still working` (actionable) → `failed` (actionable), with no infinite spinner.

**Given** an upload is in progress
**When** the user navigates to another folder/workspace (within the same session)
**Then** the upload queue/progress remains visible and continues to update, and the user can return to the original context without losing the upload status (no infinite loading, actionable failure states).

**Given** an operation exceeds its configured threshold
**When** the UI transitions out of the initial loading state
**Then** it shows an explicit “still working” or “failed” state with a clear next action (retry / contact admin / runbook link), without leaking sensitive details.

**Given** an operation fails due to environment/proxy/storage conditions
**When** the UI displays the error
**Then** the messaging remains no-leak and capability-driven, and points to operator-facing diagnostics for actionable details.

### Story 5.2: No-leak error contract (client-generic) + operator-facing `failure_class` and safe evidence

As an end user and operator,
I want a consistent no-leak error response and messaging contract where client-facing errors remain generic, while operator-facing surfaces provide actionable identifiers and safe evidence,
So that failures are diagnosable without exposing secrets, internal URLs, object keys, or paths.

**Acceptance Criteria:**

**Given** any request fails on a user-facing surface (API/UI/public share link/media/preview/WOPI/external API)
**When** an error response is returned to the client
**Then** it is clean and no-leak: no stack traces, no raw exceptions, no credentials, no internal URLs, no raw S3 object keys, and no raw mount paths/SMB details.
**And** error detail remains generic for clients (avoid revealing why a token/permission check failed).

**Given** a public MountProvider share link is opened
**When** the token is invalid (`404`) or valid but the target is missing (`410`)
**Then** the client response remains generic and no-leak (no path, no SMB info, no hints beyond the intended 404/410 semantics).
**And** operator-facing surfaces may show `failure_class` + allow-listed safe evidence + `next_action_hint` (no-leak).

**Given** the external API is enabled
**When** a caller is missing/has an invalid token (`401`) or is not allowlisted (`403`)
**Then** the client response remains generic and no-leak (no claim/audience details, no introspection reasoning).
**And** operator-facing diagnostics/artifacts provide `failure_class` + `next_action_hint` + allow-listed safe evidence (no-leak).

**Given** the same failure is observable via operator-facing surfaces (Diagnostics right panel, deterministic artifacts, or logs designed for no-leak)
**When** the operator inspects the failure
**Then** the system provides `failure_class` and `next_action_hint` plus allow-listed safe evidence only (e.g., status codes, request_id, hashes, audience codes), and never relies on “redact after the fact”.

**Given** error messaging is shown in the UI
**When** a capability is unavailable or a prerequisite is missing
**Then** the UI shows an explicit non-leaky “why” and “next action” state (no dead actions), and uses the operator-facing diagnostics as the place to get actionable technical detail.

### Story 5.3: Deterministic recovery patterns for uploads and media/edge failures (cleanup + actionable next steps)

As an end user and operator,
I want deterministic recovery behavior for common operational failures (uploads, media access, proxy/auth subrequest),
So that users can retry safely and operators get actionable guidance without leaks.

**Acceptance Criteria:**

**Given** an upload fails due to a recoverable condition (e.g., expired presigned policy, temporary storage unavailability, proxy/media-auth failure)
**When** the failure is surfaced to the user
**Then** the UI shows an actionable, time-bounded error state per Epic 5.1 (retry / re-initiate upload / contact admin), with no-leak messaging.
**And** operator-facing surfaces provide `failure_class` + `next_action_hint` + allow-listed safe evidence (no-leak).

**Given** an upload attempt creates intermediate state (e.g., item created, `upload_state=pending`)
**When** the upload does not finalize (no `upload-ended`) within its documented time window (pending TTL)
**Then** the state transition is deterministic (e.g., pending → expired/failed) and the user sees an explicit, actionable state (no infinite loading).
**And** the item is not presented as ready and exposes no media/preview surfaces until finalized.

**Given** a user retries an upload after a failure
**When** the retry targets the same pending item (idempotent retry)
**Then** the system does not create a second “ghost” item implicitly; retries are idempotent or create additional items only in an explicitly visible and controlled way.
**And** recovery is deterministic: the user can retry safely or delete the pending item without ending up with duplicates or orphaned “ready-looking” entries.

**Given** media access fails through `/media` (edge contract)
**When** the user attempts to download/preview
**Then** the client-facing failure remains generic/no-leak.
**And** operator-facing diagnostics distinguish the audience model (e.g., `INTERNAL_PROXY` vs `EXTERNAL_BROWSER` as applicable) and provide actionable next steps (proxy contract checklist, CT-S3 pointers) without leaking secrets/paths/keys.

## Epic 6: Share Links (S3) with Public Token Access

Users can create share links for S3 items; public access is token-based and works without an authenticated session when configured as public.

### Story 6.1: Configure S3 item share links (reach/role) and publish a canonical public URL

As an end user,
I want to configure share link settings for an S3-backed file or folder and obtain a canonical share URL,
So that I can share access according to Drive’s sharing model.

**Acceptance Criteria:**

**Given** I am authenticated and have permission to share an S3-backed item
**When** I configure the item’s share link settings (reach and role) via the supported API/UI
**Then** the configuration is stored deterministically and returned in the item representation as share link state.
**And** the share URL is derived from `DRIVE_PUBLIC_URL` and uses the canonical public host.

**Given** I do not have permission to configure sharing on an item
**When** I attempt to change its share link settings
**Then** the API responds deterministically (no-leak) and the UI shows an actionable state (no dead actions), per Epic 5 patterns.

### Story 6.2: Open S3 public share links without an authenticated session (token-enforced)

As an end user,
I want to open a public share link for an S3-backed file or folder without an authenticated session,
So that sharing works for recipients who are not logged into Drive.

**Acceptance Criteria:**

**Given** a share link is configured as public
**When** a recipient opens the share URL in a browser without being authenticated
**Then** access is enforced by the share token and the recipient can view the shared content within the configured reach/role.
**And** the share experience is time-bounded and actionable (no infinite loading) per Epic 5.1.

**Given** a share link is not public (or sharing is disabled)
**When** an unauthenticated recipient opens the share URL
**Then** the client response is generic/no-leak and does not reveal the item’s existence or metadata beyond the intended behavior.

## Epic 7: MountProvider Framework: Contract-level Browse/Discover + Capability Gating

Framework epic (contract-level): configure mounts, enable/disable without impacting S3, discover mounts/capabilities, browse with deterministic ordering/pagination, enforce capability gating (no dead actions), and support MountProvider share links with deterministic semantics when capability is enabled.

### Story 7.1: Operator-configured mounts registry (mount_id, provider, enabled) with deterministic validation

As an operator,
I want to configure mounts with a stable `mount_id`, display name, provider type, and provider-specific non-secret parameters,
So that mounts can be managed without changing S3-backed behavior.

**Acceptance Criteria:**

**Given** the operator provides mount configuration inputs (settings/env/file-backed configuration)
**When** configuration validation runs
**Then** each mount has a stable, unique `mount_id`, a display name, a provider type, and provider-specific non-secret parameters.
**And** invalid configuration fails early with deterministic `failure_class` + `next_action_hint`, without leaking secrets or internal paths.

**Given** a mount is disabled
**When** users browse/discover mounts
**Then** the disabled mount is not available for end-user actions, and any attempted access yields deterministic, no-leak behavior.

### Story 7.2: Discover mounts and capabilities (API + UI entry point, constants enforced)

As an end user,
I want to discover the available mounts and their capabilities via an API and a UI entry point,
So that the Explorer can render mount surfaces and actions without dead buttons.

**Acceptance Criteria:**

**Given** mounts are configured
**When** I call the mounts discovery endpoint
**Then** the response includes `mount_id`, display name, provider type, and a capability map that uses the documented constant keys (at minimum: `mount.upload`, `mount.preview`, `mount.wopi`, `mount.share_link`).
**And** the response contains no secret material and does not expose SMB connection details.

**Given** the frontend renders the mounts entry point
**When** it displays mounts and actions
**Then** the UI is capability-driven (no dead actions) and uses Epic 5 messaging patterns for disabled/unavailable capabilities.

### Story 7.3: Browse mount paths with deterministic ordering/pagination and virtual entry identifiers

As an end user,
I want to browse a mount path and see file/folder metadata with deterministic ordering and pagination,
So that mount navigation is predictable and scalable.

**Acceptance Criteria:**

**Given** a mount is enabled and the user has access
**When** the user requests the children of a mount path
**Then** the API returns a deterministic ordering and contract-level pagination/limits.
**And** each returned entry is identified as a virtual entry by `(mount_id, normalized_path)` with deterministic path normalization.

**Given** the Explorer must be capability-driven
**When** listing mount children
**Then** the list response includes the user-relevant per-entry abilities/capabilities required to render actions without dead buttons (as applicable), consistent with Epic 4 patterns for `abilities`.

### Story 7.4: Enforce capability gating across mount actions (no dead actions, deterministic errors)

As an end user,
I want mount actions (upload/download/preview/share/WOPI) to be gated by explicit capabilities and prerequisites,
So that unavailable actions are never presented as “clickable then fail”.

**Acceptance Criteria:**

**Given** a mount capability is false (e.g., `mount.preview=false`)
**When** the UI and API render/serve that action
**Then** the UI hides/disables the action with a clear, no-leak “why + next action” message, and the API rejects attempts deterministically without exposing provider internals.

**Given** a mount capability is true but a runtime prerequisite is missing/unhealthy
**When** the user attempts the action
**Then** the UI shows a time-bounded actionable state (per Epic 5.1) and the operator-facing surfaces expose `failure_class` + `next_action_hint` with safe evidence only.

### Story 7.5: Create MountProvider share links for virtual entries (capability-driven)

As an end user,
I want to create share links for MountProvider resources identified by `(mount_id, normalized_path)` when the mount supports it,
So that I can share mount content consistently with S3 sharing.

**Acceptance Criteria:**

**Given** a mount is configured and exposes the `mount.share_link` capability
**When** I request share link creation for a target `(mount_id, normalized_path)`
**Then** the system normalizes the path deterministically and stores a share-link token that maps to the virtual entry identifier.
**And** the public share URL is derived from `DRIVE_PUBLIC_URL`.

**Given** a mount does not expose the `mount.share_link` capability
**When** I attempt to create a share link for that mount
**Then** the API/UI behavior is capability-driven (no dead actions), and any client-facing error remains generic/no-leak.

### Story 7.6: Enforce deterministic public MountProvider share-link semantics (404/410) and out-of-band change behavior

As an end user and operator,
I want MountProvider public share links to have deterministic, no-leak semantics and explicit behavior for out-of-band target changes,
So that the public surface is safe and operationally diagnosable without exposing paths or SMB details.

**Acceptance Criteria:**

**Given** a public MountProvider share link is opened (unauthenticated recipient)
**When** the token is unknown/invalid
**Then** the response is `404` and remains generic/no-leak (no path, no SMB info, no stack traces).

**Given** a public MountProvider share link is opened (unauthenticated recipient)
**When** the token is valid/known but the target is missing (e.g., renamed/moved/deleted out-of-band)
**Then** the response is `410` and remains generic/no-leak (no path, no SMB info, no stack traces).
**And** the UI shows an explicit, actionable state (e.g., “Link expired or target moved”) without technical details, per Epic 5.

**Given** the operator inspects the failure via operator-facing surfaces (Diagnostics right panel and/or deterministic artifacts)
**When** the share link fails with `404` or `410`
**Then** operator-facing details include `failure_class` + `next_action_hint` and allow-listed safe evidence only.
**And** any mount path evidence uses `path_hash` (HMAC) rather than exposing `normalized_path`.

## Epic 8: Mount Secrets: Refs-only Resolution + Hot Rotation

Operators can reference secrets (ref/path) in mount configuration; the system resolves secrets at runtime without leaks, enforces refs-only semantics, deterministic precedence, and rotation without restart; session reuse across rotation is safe.

### Story 8.1: Refs-only secret fields for mounts (never store/return/log secret material)

As an operator,
I want mount credentials to be expressed only as secret references (env var name and/or file path),
So that secret values are never stored in the database, returned by APIs, or leaked into logs/artifacts.

**Acceptance Criteria:**

**Given** a mount requires credentials
**When** the operator configures the mount
**Then** the configuration stores only references (e.g., `password_secret_ref` and/or `password_secret_path`), never secret values.
**And** secret references are not exposed on end-user APIs; they are provided only via operator-managed configuration (env/files) in v1 (no in-app admin UI in this project).

**Given** any mount-related API response, log line, or deterministic artifact is produced
**When** it includes mount configuration context
**Then** it never includes secret values and avoids leaking sensitive file paths; errors remain no-leak and generic for client-facing surfaces.

### Story 8.2: Centralized secret resolver with deterministic precedence (file > env) and bounded refresh

As an operator,
I want a centralized, provider-agnostic secret resolver with deterministic precedence and bounded refresh,
So that providers can fetch secrets consistently without restarts and without duplicating resolver logic.

**Acceptance Criteria:**

**Given** both `password_secret_path` and `password_secret_ref` are configured
**When** a provider requests the secret value at runtime
**Then** resolution precedence is deterministic and documented: file path > env ref.

**Given** the resolver caches secret values for performance
**When** the configured refresh interval elapses or the resolver detects a change (implementation-defined)
**Then** subsequent operations observe updated secret values within a bounded, operator-configurable time.

**Given** secret resolution fails (missing file/env, permission denied, malformed)
**When** the failure is returned to clients
**Then** client-facing errors remain generic/no-leak, and operator-facing surfaces provide `failure_class` + `next_action_hint` plus allow-listed safe evidence only.

### Story 8.3: Safe connection/session reuse across secret rotation (no stale credentials, no leaks)

As an operator,
I want secret rotation to be safe with connection/session reuse,
So that stale credentials are not reused after rotation and failures do not leak sensitive material.

**Acceptance Criteria:**

**Given** a secret value changes (rotation)
**When** new mount operations begin after the bounded refresh window
**Then** new connections/sessions use the updated credentials.

**Given** a connection/session is pooled or reused
**When** the resolver indicates credentials have changed
**Then** reuse is safe: stale sessions are not used for new operations (or are deterministically re-authenticated) and failures remain no-leak.

## Epic 9: SMB Mount v1 Provider: Streaming Upload/Download/Preview (Implementation-level)

Provider epic (implementation-level): SMB-specific configuration + backend-mediated streaming download/upload and preview where supported, implemented on top of the Epic 7 framework contracts; share links are handled via Epics 6 (S3) and 7 (MountProvider), and WOPI via Epic 10.

### Story 9.1: SMB mount configuration schema and deterministic validation (refs-only secrets)

As an operator,
I want to configure an SMB mount with explicit connection parameters and refs-only secrets,
So that SMB mounts are deployable in self-host environments without storing secrets in the database.

**Acceptance Criteria:**

**Given** an operator configures an SMB mount
**When** configuration validation runs
**Then** required fields are validated deterministically (at minimum: `server`, `share`, `username`; `port` defaultable; `domain/workgroup` optional; optional `base_path` and timeouts).
**And** password credentials are configured only via secret references per Epic 8 (refs-only; deterministic precedence).

**Given** invalid SMB configuration is provided
**When** validation runs
**Then** it fails early with deterministic `failure_class` + `next_action_hint`, with no-leak errors (no secret/path leaks).

### Story 9.2: SMB provider implements the mount browse contract (list/stat) with deterministic ordering

As a user,
I want SMB-backed mounts to support directory listing and metadata lookup through the MountProvider interface,
So that the Epic 7 browse endpoints can work without SMB-specific endpoints or duplicated browse implementations.

**Acceptance Criteria:**

**Given** an SMB mount is enabled
**When** a mount browse request is executed through the provider interface
**Then** the provider returns directory entries with deterministic ordering and normalized paths.
**And** provider errors are mapped to deterministic, no-leak failures (no raw stack traces, no credential leaks, no raw SMB path leaks).

### Story 9.3: SMB streaming download with Range support where applicable

As an end user,
I want to download SMB-backed mount files via backend-mediated streaming (with Range where supported),
So that large downloads work efficiently and reliably.

**Acceptance Criteria:**

**Given** I download a mount file from an SMB mount
**When** the backend serves the download
**Then** it streams content without buffering the entire file in memory (NFR1).

**Given** the client sends a Range request and the SMB provider supports range reads
**When** the backend serves the response
**Then** it returns a correct partial response (e.g., `206` with appropriate headers) and remains deterministic and no-leak on failures.

### Story 9.4: SMB streaming upload (large-file capable) with deterministic finalize semantics

As an end user,
I want to upload files to an SMB-backed mount via backend-mediated streaming with deterministic finalize behavior,
So that large uploads succeed reliably without creating “ghost” entries on failure.

**Acceptance Criteria:**

**Given** I upload a file to an SMB-backed mount
**When** the backend processes the upload
**Then** it streams the upload (no full buffering) and applies documented limits/timeouts/concurrency controls.

**Given** an upload uses a temp/intermediate target (implementation-defined)
**When** the upload completes successfully
**Then** finalize semantics are deterministic (e.g., temp → final rename best-effort) and the resulting entry is visible in browse.

**Given** the upload fails or is interrupted
**When** the user refreshes or retries
**Then** the system behaves deterministically per Epic 5.3 (no implicit ghost “ready” entries; actionable failure state; idempotent retry semantics where applicable).

### Story 9.5: SMB preview support is explicit, capability-driven, and deterministic

As an end user,
I want preview behavior for SMB-backed files to be explicit and deterministic,
So that “preview not available” is distinct from “access denied” and the UI never relies on heuristics.

**Acceptance Criteria:**

**Given** an SMB mount exposes `mount.preview=true`
**When** I open a preview for a supported file
**Then** the backend serves preview content through the supported preview surface with deterministic behavior and no-leak errors.

**Given** an SMB mount does not expose `mount.preview` (or prerequisites are missing)
**When** I attempt to preview a file
**Then** the UI shows an explicit “preview not available” state (distinct from access denied) with a next action, per Epic 5.

## Epic 10: WOPI/Collabora Editing (Capability-driven, Enabled & Healthy)

WOPI actions appear only when prerequisites are met per backend; if S3 prerequisites (e.g., bucket versioning) are not met, WOPI is disabled with operator guidance; MountProvider WOPI uses app-level version string and lock semantics; users can launch WOPI editing via reverse-proxy-compatible flow; host allowlist derives from `DRIVE_PUBLIC_URL`; edits save back through the supported write pipeline.

### Story 10.1: WOPI enablement configuration (host allowlist, HTTPS posture, health gating)

As an operator,
I want to configure WOPI/Collabora integration with strict host allowlisting derived from `DRIVE_PUBLIC_URL` and clear health gating,
So that WOPI is safe-by-default and “enabled & healthy” is explicit and operator-debuggable.

**Acceptance Criteria:**

**Given** WOPI is enabled by configuration
**When** configuration validation runs
**Then** allowlisted WOPI hosts/origins are derived from `DRIVE_PUBLIC_URL` by default and are validated deterministically (no wildcards, no ambiguous parsing).
**And** production requires HTTPS for WOPI-related public surfaces (dev override only if explicitly enabled, consistent with Epic 1/2 TLS rules).

**Given** WOPI is enabled
**When** operator-facing diagnostics/health checks run
**Then** the system exposes an “enabled & healthy” vs “enabled but unhealthy” vs “disabled” state with `failure_class` + `next_action_hint` and allow-listed safe evidence only (no-leak).

### Story 10.2: Capability-driven WOPI action exposure per backend (no dead buttons)

As an end user,
I want WOPI editing actions to appear only when the backend supports them and prerequisites are met,
So that the UI never offers a dead WOPI action.

**Acceptance Criteria:**

**Given** I browse files on S3 or a mount
**When** the API returns item/entry abilities
**Then** WOPI edit actions are exposed only when the integration is enabled & healthy and the backend-specific prerequisites are satisfied.
**And** when unavailable, the UI provides a clear “why + next action” state without leaking operator-only detail (Epic 5 patterns).

### Story 10.3: Reverse-proxy-compatible WOPI launch flow with short-lived tokens

As an end user,
I want to launch WOPI editing for an eligible file through a reverse-proxy-compatible flow,
So that WOPI works in self-host environments without direct internal network access.

**Acceptance Criteria:**

**Given** WOPI is enabled & healthy and a file is eligible
**When** I launch WOPI editing
**Then** the system issues a short-lived, no-leak WOPI access token and redirects/loads the WOPI client in a way compatible with reverse proxies.
**And** client-facing failures remain generic/no-leak; operator-facing surfaces provide `failure_class` + `next_action_hint`.

### Story 10.4: S3 WOPI prerequisite validation (bucket versioning) with operator guidance

As an operator,
I want S3 WOPI to be disabled when S3 prerequisites (e.g., bucket versioning) are not met, with clear guidance,
So that operators can remediate instead of debugging opaque runtime failures.

**Acceptance Criteria:**

**Given** WOPI is enabled but the S3 backend prerequisite is not satisfied
**When** the system evaluates backend prerequisites
**Then** WOPI is disabled for S3-backed files and operator-facing surfaces provide a deterministic `failure_class` + `next_action_hint` referencing the remediation steps.

### Story 10.5: MountProvider WOPI semantics: version string + locks (TTL/release/conflict) + streaming save pipeline

As an end user and operator,
I want WOPI on mounts to enforce deterministic version and lock semantics and stream saves back to the underlying provider,
So that collaborative editing is correct, efficient, and diagnosable without leaks.

**Acceptance Criteria:**

**Given** a mount exposes `mount.wopi=true`
**When** WOPI operations occur for that mount
**Then** the system computes a deterministic application-level version string that changes when content changes.

**Given** a WOPI session attempts to lock a mount-backed file
**When** a lock exists or expires
**Then** lock semantics are deterministic (TTL, release, conflict handling) and do not leak mount paths or credentials.

**Given** WOPI saves content back to a mount-backed file
**When** PutFile (or equivalent) is invoked
**Then** the backend streams the write through the provider (NFR1), and failures are surfaced as generic/no-leak to clients with operator-facing `failure_class` + `next_action_hint`.

## Epic 11: Storage Correctness Proof: CT-S3 (SeaweedFS Baseline, Audience-aware)

Developers/CI can run Drive-integrated S3 contract tests with explicit audiences; reports capture safe evidence without leaks; v1 supports SeaweedFS as the blocking baseline provider profile encoded as repeatable tests and runbook checks.

### Story 11.1: Drive-integrated CT-S3 runner with explicit audience model and deterministic reports

As a developer/operator,
I want to run Drive-integrated S3 contract tests (CT-S3) with explicit audiences and deterministic reporting,
So that self-host deployments can prove the `/media` + SigV4 + upload/preview contracts against the supported S3 profiles.

**Acceptance Criteria:**

**Given** a target S3 provider profile is configured (SeaweedFS baseline in v1)
**When** I run the CT-S3 suite via the documented entrypoint (local and CI)
**Then** tests exercise the explicit audience model (`INTERNAL_PROXY` vs `EXTERNAL_BROWSER`) and validate the documented invariants (e.g., connect URL vs signed host expectations).
**And** results are written as deterministic artifacts (human-readable + machine-readable) suitable for operator diagnostics.

### Story 11.2: Encode SeaweedFS as the blocking baseline profile (repeatable checks + runbook alignment)

As a developer/operator,
I want SeaweedFS S3 gateway behavior encoded as the blocking CT-S3 baseline profile with repeatable checks,
So that “works on SeaweedFS” is a deterministic, enforceable v1 promise.

**Acceptance Criteria:**

**Given** the SeaweedFS profile is selected
**When** CT-S3 runs
**Then** the baseline expectations are explicit, repeatable, and produce stable `failure_class` + `next_action_hint` on failure.
**And** the self-host runbooks reference these checks for troubleshooting and validation.
**And** Sprint 0 deliverables align the default self-host/dev/CI baseline to SeaweedFS (compose/runbooks/gates), so “blocking baseline” is true in practice, not only in documentation.
**And** the default Docker/compose path uses SeaweedFS for S3 (MinIO may remain only as an explicitly non-blocking fixture and must not be treated as the v1 baseline in docs, gates, or runbooks).

### Story 11.3: Safe evidence allow-listing for CT-S3 (no-leak by construction)

As an operator,
I want CT-S3 evidence to be allow-listed and no-leak by construction,
So that reports help debugging without exposing credentials, paths, internal URLs, or object keys.

**Acceptance Criteria:**

**Given** CT-S3 produces evidence for any failed check
**When** the report is generated
**Then** evidence is restricted to allow-listed fields (e.g., status codes, request_id, keyed hashes, latency buckets, audience codes) and never includes secrets, raw object keys, or internal URLs.

## Epic 12: Deterministic Delivery System: Gates, Artifacts, failure_class, Strict Mirror

Developers/CI can run stable `gate_id`s via a gates runner, producing deterministic artifacts; failures are classified with stable `failure_class` values and a `next_action_hint`; registry fingerprint (B+) is embedded and drift is blocked; no-leak is enforced with scanning scope limited to `_bmad-output/**` text artifacts. This epic wires CT-S3 gates that run the suite delivered by Epic 11.

### Story 12.1: Gates runner executes stable `gate_id`s and writes deterministic artifacts

As a developer/CI,
I want a gates runner that executes checks via stable `gate_id`s and writes deterministic artifacts,
So that CI and local runs produce consistent, machine-readable results with preserved evidence.

**Acceptance Criteria:**

**Given** a list of `gate_id`s is requested
**When** the runner executes them
**Then** it resolves `gate_id`s to the underlying commands deterministically and records `result`, `duration_ms`, and when failing `failure_class` + `next_action_hint`.
**And** artifacts are written under `_bmad-output/implementation-artifacts/` in deterministic locations, including a stable “latest” pointer.

### Story 12.2: Standardize `failure_class` + `next_action_hint` across gates and operator-facing artifacts

As an operator/developer,
I want failures to be classified with stable `failure_class` values and actionable `next_action_hint`s,
So that troubleshooting is consistent across CT-S3, mounts integration checks, E2E, and mirror enforcement.

**Acceptance Criteria:**

**Given** any gate fails
**When** artifacts are produced
**Then** the artifact schema includes `failure_class` and `next_action_hint` as first-class fields and avoids embedding sensitive detail in the failure code itself.
**And** evidence remains allow-listed and no-leak (Epic 11.3 / Epic 5.2).

### Story 12.3: Strict mirror enforcement (BMAD registry source-of-truth; GitHub fork mirror only)

As a developer/CI,
I want strict mirror enforcement using a registry fingerprint (B+) embedded in issue/PR bodies,
So that GitHub remains a strict projection of BMAD local artifacts/registry and drift is blocked deterministically.

**Acceptance Criteria:**

**Given** a work item is mirrored into a GitHub issue/PR
**When** the fingerprint is computed and embedded
**Then** the fingerprint is computed from the canonical subset (B+) and excludes dynamic fields (status/runs/timestamps).

**Given** a PR is updated manually or diverges from the registry
**When** CI (and/or the runner) checks strict mirror integrity
**Then** it fails deterministically with `failure_class` + `next_action_hint` and clearly states that BMAD local artifacts/registry are the source of truth.

### Story 12.4: Wire CT-S3 and no-leak scanning into CI with strict scope; enforce dependency automation policy

As a developer/CI,
I want CT-S3 and no-leak scanning wired into CI via stable gates with strict scanning scope,
So that v1 promises are enforced without noisy false positives or scope drift.

**Acceptance Criteria:**

**Given** `s3.contracts.seaweedfs` (or equivalent) gate is executed
**When** the gates runner resolves it
**Then** it invokes the CT-S3 suite delivered by Epic 11 and records results in deterministic artifacts.

**Given** no-leak scanning runs in CI
**When** it evaluates generated artifacts
**Then** automated scanning scope is limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) while preserving the global “no-leak everywhere” requirement.

**Given** `e2e.chrome` runs for scoped v1 flows
**When** accessibility checks are executed (axe-based, “no regressions”)
**Then** the run produces retained artifacts for the checked surfaces and fails deterministically with `failure_class` + `next_action_hint` on serious/critical violations, without leaking secrets or sensitive paths/keys.

**Given** dependency automation is configured
**When** the repository automation is validated
**Then** Renovate is the mechanism for version-bump PRs, and Dependabot is limited to security alerts only (no Dependabot PR configuration is introduced).
