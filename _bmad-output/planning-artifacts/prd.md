---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-drive-20260203-200136.md
  - _bmad-output/planning-artifacts/handoff/brainstorming-handoff.md
  - _bmad-output/brainstorming/brainstorming-session-20260203-110252.md
  - _bmad-output/planning-artifacts/architecture/architecture-kickoff-brief.md
  - _bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md
  - _bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md
  - _bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md
  - _bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md
  - _bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md
  - _bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md
  - _bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md
  - _bmad-output/planning-artifacts/upstream/drive-open-backlog.md
  - _bmad-output/planning-artifacts/upstream/drive-open-issues.json
  - _bmad-output/planning-artifacts/upstream/drive-open-prs.json
  - docs/architecture.md
  - docs/ds_proxy.md
  - docs/entitlements.md
  - docs/env.md
  - docs/installation/kubernetes.md
  - docs/installation/README.md
  - docs/metrics.md
  - docs/release.md
  - docs/resource_server.md
  - docs/setup-find.md
  - docs/theming.md
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 2
  projectDocs: 11
  automation: 0
  storage: 3
  packaging: 1
  wopi: 1
  sources: 2
  upstream: 3
classification:
  projectType: web_app
  domain: govtech
  complexity: high
  projectContext: brownfield
workflowType: prd
workflow: edit
project_name: drive
author: Apoze
date: 2026-02-03T20:52:28Z
lastEdited: 2026-02-03T23:49:20Z
editHistory:
  - date: 2026-02-03T23:37:51Z
    changes: 'Fix GovTech special sections (procurement/restricted env/transparency); add NFR verification phrasing; reword strict FRs to enforcement phrasing; add light “validated via” hints in Success Criteria.'
  - date: 2026-02-03T23:49:20Z
    changes: 'Tighten measurability phrasing (FR36/FR42) and add explicit measurable criteria/context to NFRs while keeping operator-neutral constraints.'
document_output_language: English
communication_language: Français
---

# Product Requirements Document - drive

**Author:** Apoze
**Date:** 2026-02-03T20:52:28Z

## Executive Summary

`Apoze/drive` evolves Drive into a production-usable **self-hosted** file service while preserving upstream-like discipline (clean boundaries, tests, CI, conventions) to keep optional future upstreaming possible (human decision).

**Product pillars (v1 focus):**
- **Self-host packaging & operations:** proxy-agnostic edge contract (Nginx reference), canonical public base URL (`DRIVE_PUBLIC_URL`), TLS strategy, backup/restore + upgrade/rollback runbooks, deterministic smoke checks.
- **Storage correctness:** Drive-integrated **S3 contract tests** with explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER) and safe evidence (no-leak), baseline provider profile SeaweedFS (blocking).
- **Storage extensibility:** a Drive-native **MountProvider framework** enabling a first mount provider (SMB) with a Filestash-grade gateway behavior (server-mediated upload/download, preview, share links, WOPI), without rewriting the S3-first core.
- **Docs-first delivery:** acceptance criteria live in `_bmad-output/` planning artifacts; GitHub issues/PRs may mirror those decisions manually for collaboration. (No automated strict-mirror enforcement is assumed.)

**Non-negotiables:**
- Repo scope: work happens only in `Apoze/drive` (no upstream interactions).
- Evidence/no-leak: reports/artifacts must avoid secrets, credentials, and raw sensitive paths/keys.
- E2E: Chrome-only for determinism (host-first), artifacts retained.

## Project Classification

- **Project Type:** Web app (SPA-like Next.js) + Django/DRF backend
- **Domain:** GovTech (high compliance/operability expectations; exact legal compliance remains deployment-context dependent)
- **Complexity:** High
- **Project Context:** Brownfield (existing system + new capabilities)

## Success Criteria

### User Success

- Self-host operators can deploy Drive reliably (Docker + Nginx edge baseline and Kubernetes path) with documented, repeatable procedures.
- Operators configure a single canonical public base URL (`DRIVE_PUBLIC_URL`) used to derive all public URLs (redirects, share links, WOPI allowlists, CORS origins), while allowing separate internal/service URLs where appropriate (e.g., internal API/media/storage endpoints).
- Storage “just works” across the supported S3-compatible profile(s) with deterministic evidence on failures (failure_class + safe evidence).
- Users can access a second storage space (SMB mount) inside Drive as a complete SMB Mount v1 feature set: browse/read, upload, preview, share links, and WOPI (capability-driven), without changing existing S3 flows.
- **Validated via:** config preflight (`config_preflight` management command) + documented smoke checklist + backend tests + frontend unit/lint + Chrome-only E2E where applicable.

### Business Success

- Reduced operator burden for self-hosting Drive via runbooks + preflight + deterministic gates.
- Maintains upstream-like discipline (small PRs, clear boundaries, tests/CI) to preserve optional future upstreaming (human decision).
- Documentation stays consistent: PRs/issues reference the relevant `_bmad-output/` artifact(s), and validation steps are captured in reviewable form.

### Technical Success

- Checks are runnable locally via stable Make targets (e.g. `make lint`, `make test-back`, `make frontend-lint`, and `make run-tests-e2e`).
- Optional (future): strict mirror enforcement (fingerprints/templates/CI checks) can be added later, but is not required for the current dev workflow.
- No-leak is enforced globally; automated scanning scope is limited to `_bmad-output/**` text artifacts only (`.md`, `.json`, `.txt`) to avoid false positives.
- S3 contract tests are Drive-integrated with explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER) and `connect_url` vs `signed_host` invariants; the same audience model is documented in runbooks/docs, not only encoded in tests.
- MountProvider is a plugin-like boundary for non-S3 backends (SMB now, others later) and must avoid rewriting the existing S3-first core behavior.
- SMB mount backend has deterministic integration tests (Samba container) and clear failure classes; WOPI for SMB uses an app version string + locks (does not depend on S3 bucket versioning) and must remain compatible with Collabora discovery and reverse proxy constraints.
- **Validated via:** recorded CI/test output + `make test-back` + (when implemented) CT-S3 and mount integration test suites; keep troubleshooting artifacts under `_bmad-output/implementation-artifacts/` when useful.

### Measurable Outcomes

- Time-to-first-successful-deploy (Docker + Nginx edge, dev machine): ≤ 30 minutes from “clone + env” to “login + upload works”, using the provided bootstrap/preflight scripts (initial target; may be revised with evidence).
- Restore validation: a post-restore smoke checklist validates login, list files, upload, and media access via `media-auth`.
- CI: mandatory gates remain green for required axes; flaky behavior follows quarantine policy (max 1 retry, expiry).
- Storage correctness: `s3.contracts.seaweedfs` passes in CI for the baseline provider profile; ds-proxy compatibility remains optional/non-blocking unless explicitly promoted later.
- No-leak scan: 0 leaks in `_bmad-output/**` text artifacts.

## Product Scope

### v1 Strategy

v1 is a functional **self-host baseline** focused on operability, storage correctness (contract-first), and extensibility (MountProvider), rather than a minimal feature slice.

### v1 Scope (Selfhost Baseline)

- Packaging baseline: canonical `DRIVE_PUBLIC_URL`, config validation, Nginx edge templates (dev+prod aligned), dev TLS automation, documented prod TLS paths, backup/restore + upgrade/rollback runbooks + smoke checklist.
- Automation baseline (optional): deterministic checks and a consistent failure taxonomy (`failure_class` + safe evidence + `next_action_hint`) to support supportability and CI.
- Storage correctness baseline: Drive-integrated S3 contract tests with the explicit audience model, plus matching documentation/runbooks.
- Storage extensibility baseline: MountProvider interface + mount configuration model + mounts API.
- SMB Mount v1 (full scope): browse/read, upload, preview, share links, and WOPI; with explicit accepted constraints:
  - No synchronization between SMB and S3
  - Global mount permissions (single service account), no per-path SMB RBAC
  - Share links are path-based and may break on out-of-band SMB path changes
  - Error semantics:
    - `404` for unknown/invalid share token
    - `410` when the share token is valid but the target path no longer exists (deleted/moved out-of-band)

### Delivery & Risk Mitigation

- **Core skill coverage (expected):** backend (storage/contracts/mounts/WOPI), frontend (mounts UX/capability gating/share+WOPI flows), infra/ops (reverse proxy contract, Docker/K8s packaging, TLS, runbooks), QA (CT-S3, Samba integration tests, Chrome-only E2E).
- **Primary technical risks:** proxy/media contract drift (`/media` auth subrequest + SigV4 header propagation incl. optional STS token), provider/proxy S3 compatibility gaps, SMB semantics/timeouts/atomicity, WOPI correctness/locking/version behavior, requirements/docs drift.
- **Mitigation approach:** PR-friendly sequencing, deterministic gates and artifacts, safe evidence (no-leak), and documented operator runbooks + smoke checks.

### Growth Features (Post-v1)

- Additional S3 provider profiles (e.g., Ceph RGW) and proxy profiles (ds-proxy) validated via CT-S3 evidence.
- Expanded mount providers beyond SMB, without refactoring S3-first core.
- Broader E2E coverage as stability permits (Chrome-only by default).

### Vision (Future)

- Declarative provider/mount capability catalog and more automated diagnostics (still no-leak).
- Optional performance harnesses outside core CI.

## User Journeys

### Journey 1 — Self-host Operator: bootstrap → config → deploy → smoke

**Persona:** Alex (Self-host Operator / Platform Engineer)

**Opening Scene**

Alex has been asked to run Drive as a production-grade self-hosted file service. They already have (or can bring) an **external OIDC IdP** (bring-your-own) and an existing reverse proxy. They need a predictable, documented setup that doesn’t turn into a week of debugging `/media` issues and storage quirks.

**Rising Action**

- Alex runs a bootstrap/preflight command to validate prerequisites (tooling, required secrets, URL consistency, storage endpoints separation).
- Alex sets `DRIVE_PUBLIC_URL` as the canonical public base URL and confirms derived values (redirect hosts, WOPI allowlist inputs, share link base URL, CORS origins).
- Alex configures object storage endpoints with the explicit audience model:
  - **INTERNAL/PROXY** (backend/edge) invariants: “signed host == used host”.
  - **EXTERNAL/BROWSER** (presigned upload) invariants: browser-facing host is correct and consistent with `DRIVE_PUBLIC_URL`/proxy strategy.
- Alex chooses an edge deployment:
  - uses the provided **Nginx edge templates** as the baseline (recommended), **or**
  - maps the same contract behavior into their own reverse proxy (supported as long as the contract is preserved).
- Alex deploys using Docker+edge baseline and/or Kubernetes (Ingress path), then follows the documented smoke checklist.

**Climax**

Alex performs the first “real” validation: login succeeds, upload succeeds, and media access works via the `media-auth` contract (no 403 loops, no signature mismatch). When something fails, the system returns a stable `failure_class` and safe evidence.

**Resolution**

Drive is operational with a stable configuration surface. Alex has runbooks for backup/restore and upgrade/rollback, and knows exactly what to verify after changes.

**Failure & Recovery Moments**

- Misconfigured `DRIVE_PUBLIC_URL` → preflight blocks early with deterministic `failure_class` and `next_action_hint`.
- INTERNAL/EXTERNAL storage endpoints mixed → contract tests/doc checklist identify the mismatch before it reaches production.
- Proxy configuration drift (`/media` auth_request) → documented contract + smoke tests pinpoint the breakage.

---

### Journey 2 — End User (S3): upload → preview → share → WOPI (when available)

**Persona:** Inès (Knowledge Worker)

**Opening Scene**

Inès needs to store and collaborate on documents with confidence that uploads, previews, and share links behave consistently.

**Rising Action**

- Inès logs in via OIDC and lands in Drive.
- She uploads a file to S3-backed storage (browser flow using presigned upload).
- She previews the file and shares it via a share link.
- If WOPI is enabled for the backend (i.e., prerequisites are satisfied), she opens the file in the WOPI client and edits collaboratively.

**Climax**

The moment of trust: upload completes, preview loads, share link works, and WOPI edit does not cause data loss or confusing version conflicts.

**Resolution**

Inès reliably collaborates on documents. The UI hides actions that are unavailable (capability-driven), avoiding dead buttons.

**Failure & Recovery Moments**

- Presigned upload fails due to audience/host mismatch → contract tests and operator guidance make the failure diagnosable (no-leak evidence).
- WOPI unavailable because prerequisite not met (e.g., versioning requirement) → the UI/API provides a clear operator-facing message; WOPI action is hidden/disabled (capability-driven).

---

### Journey 3 — End User (SMB Mount v1): browse → upload → preview → share → WOPI + out-of-band path changes

**Persona:** Malik (Knowledge Worker with legacy SMB share)

**Opening Scene**

Malik’s organization has legacy files on an SMB share. They want Drive to provide a second “storage space” without syncing it into S3.

**Rising Action**

- Malik opens the “Mounts” entry and selects the SMB mount.
- He browses folders and downloads a file (backend gateway streaming).
- He uploads a file to SMB (streaming write, best-effort atomic finalize).
- He previews a file (range when supported, explicit fallback or disablement when not).
- He creates a share link and opens it from a different device.
- He opens the file via WOPI (SMB backend uses app version string + locks; does not depend on S3 bucket versioning).

**Climax**

Malik edits a file via WOPI and sees changes saved back into SMB correctly, with predictable locking behavior and without leaking SMB paths or credentials in logs.

**Resolution**

Drive becomes a safe “gateway” for SMB collaboration. Capabilities remain explicit; the UI only exposes what the backend can guarantee.

**Failure & Recovery Moments**

- The SMB path is renamed/moved outside Drive:
  - share link token unknown/invalid → `404`
  - share link token valid but target missing → `410`
- SMB environment issues (unreachable/auth/share missing) → stable `failure_class` (no stack traces) and no-leak evidence.

---

### Journey 4 — Organization Integrator / SRE: integrate into the “suite” + reverse proxy constraints

**Persona:** Sam (Organization Integrator / SRE)

**Opening Scene**

Sam integrates Drive into a broader platform: external OIDC IdP, resource server usage, entitlements, metrics export, theming, and standardized reverse proxy policy.

**Rising Action**

- Sam configures Drive to work with the external IdP and validates allowed redirect hosts derived from `DRIVE_PUBLIC_URL`.
- Sam enables and validates suite integrations:
  - entitlements endpoint behavior (capability/permission checks),
  - resource server routes exposure and authorization model,
  - metrics route enablement and API-key operational handling,
  - theming customization via configuration.
- Sam ensures reverse proxy constraints are respected (TLS requirements, header forwarding, WOPI discovery compatibility).

**Climax**

The “platform readiness” moment: Drive works as a component within the suite without special-case hacks, and its public URLs and proxy behavior are predictable across environments.

**Resolution**

Sam can operate Drive like other suite services, with stable configuration, documented runbooks, and deterministic gates for changes.

---

### Journey 5 — Support / Troubleshooting: incident → classify → evidence → fix loop

**Persona:** Léa (Support Engineer / On-call)

**Opening Scene**

An operator reports “uploads failing” or “WOPI editing broken” after a change. Léa needs fast diagnosis without leaking secrets in tickets or artifacts.

**Rising Action**

- Léa reproduces the failure using the relevant Make targets/tests and collects troubleshooting artifacts under `_bmad-output/implementation-artifacts/` when needed.
- She reads the test output / artifacts and identifies the stable `failure_class` and `next_action_hint` (where implemented).
- She verifies whether the failure is in:
  - requirements/docs drift,
  - packaging/proxy contract (`media-auth`),
  - S3 audience mismatch (INTERNAL/EXTERNAL),
  - SMB mount environment/integration tests,
  - WOPI discovery/proxy constraints.

**Climax**

The incident becomes actionable: there is enough safe evidence to fix or rollback with confidence, without sharing raw credentials, raw SMB paths, or sensitive object keys.

**Resolution**

Léa resolves the issue and ensures local docs remain the source of truth (update `_bmad-output/` if needed), and updates any related GitHub issue/PR notes accordingly.

### Journey Requirements Summary

- **Self-host baseline requirements:** canonical public URL, validated config model, proxy contract runbooks, backup/restore + upgrade/rollback procedures, deterministic smoke checks.
- **Storage correctness requirements:** Drive-integrated CT-S3 with explicit audiences and safe evidence; documentation must mirror the audience model used in tests.
- **Mounts requirements:** MountProvider as a plugin-like boundary, mounts API + UI entrypoint, SMB integration tests and failure classes, capability-driven UX.
- **Share links requirements:** explicit error semantics (`404` unknown token vs `410` token valid but target missing), accepted constraints for out-of-band path changes.
- **WOPI requirements:** capability-driven enablement, SMB version string + locks + save pipeline, compatibility with Collabora discovery and reverse proxy constraints.
- **Automation requirements (optional):** reproducible, no-leak artifacts and a stable failure taxonomy; automated scanning limited to `_bmad-output/**` text artifacts.

## Domain-Specific Requirements

### Compliance & Regulatory

- **Accessibility baseline (product requirement):** Drive must maintain **WCAG 2.1 Level AA compatibility** (no regressions). Formal RGAA/WCAG audits and any conformance claim remain **operator-owned** and deployment-context dependent.
- **Public-sector context note:** accessibility expectations are typically stronger in public-sector environments (audits, remediation plans), but legal compliance scope and enforcement remain deployment-context dependent.

### Procurement Compliance (Operator-owned; Deployment-context dependent)

- Drive must remain deployable and supportable in procurement-constrained environments where operators require:
  - explicit versioning and pinning of runtime dependencies (images, packages) and an operator-friendly dependency inventory for the deployed stack;
  - documented supply-chain assumptions and upgrade provenance (what changes, where artifacts come from, and what is required to mirror them);
  - reproducible, documented installation/upgrade paths that avoid unexpected runtime downloads.

### Restricted Environments & Security Clearance (Operator-owned; Deployment-context dependent)

- Drive must support deployment patterns common in restricted environments:
  - compatibility with network segmentation and strict egress policies (no runtime outbound calls beyond explicitly configured external dependencies such as IdP, DB, object storage);
  - operation behind user-managed reverse proxies and private DNS while preserving the edge/media contracts;
  - the ability to mirror required container images and dependencies for air-gapped deployments, with documentation of what must be mirrored and how to validate success.

### Transparency & Auditability (Operator-owned; Deployment-context dependent)

- Drive must support operator expectations around auditability and transparency, including:
  - audit-friendly logs and deterministic artifacts for changes and failures (stable `failure_class`, safe evidence, retained gate outputs);
  - clear runbooks for incident response, backup/restore validation, and upgrade/rollback evidence collection;
  - explicit “no-leak” constraints that prevent sensitive data from being exposed in tickets, logs, or generated artifacts.

### Technical Constraints

- **Security-by-default (operator-neutral):** Drive must document threat surfaces and enforce safe defaults: secure secret management, least privilege, audit-friendly logging and artifact generation (**no credentials in logs/artifacts**), and incident-oriented runbooks.
- **Config validation & preflight (security+ops):** configuration must be validated early (including `DRIVE_PUBLIC_URL` and endpoint consistency), and preflight should block unsafe/misconfigured deployments with deterministic failure classes (no-leak evidence).
- **Identity boundary:** external OIDC IdP is bring-your-own; Drive must not assume it “provides an IdP”.
- **TLS and reverse proxy reality:** production setups must work behind a user-managed reverse proxy; Nginx is a baseline reference implementation, but required edge contracts must be proxy-agnostic.
- **No-leak enforcement:** no-leak is enforced globally for APIs/logs/artifacts; automated scanning applies only to `_bmad-output/**` **text artifacts** (`.md`, `.json`, `.txt`) to avoid false positives.

### Integration Requirements

- **Suite integration:** support entitlements, resource server usage, metrics export route, and theming customization as per existing project documentation.
- **Storage audience model (S3):** document and operationalize INTERNAL/PROXY vs EXTERNAL/BROWSER separation (not only in tests); ensure runbooks cover validation steps.
- **WOPI constraints:** WOPI must remain compatible with Collabora discovery and reverse proxy constraints, and must be **capability-gated per storage backend** (core S3 vs MountProvider-based mounts).

### Risk Mitigations

- **Self-host drift / proxy misconfig:** mitigate via validated config model, documented edge contracts, and deterministic smoke checks.
- **S3 “compatibility gaps” (SeaweedFS first):** mitigate via Drive-integrated CT-S3 suite and safe evidence.
- **SMB operational fragility:** mitigate via deterministic Samba integration tests, configurable timeouts/concurrency, and stable failure classes.
- **Requirements/docs drift:** mitigate by keeping acceptance criteria in `_bmad-output/` and referencing them from PRs/issues.

## Innovation & Novel Patterns

### Detected Innovation Areas

- **Contract-first storage support:** Drive-integrated S3 contract tests with explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER) and clear host invariants (`connect_url` vs `signed_host`), producing safe evidence (no-leak).
- **Deterministic supportability model:** stable `failure_class` + safe evidence + reproducible artifacts that make implementation, review, and troubleshooting efficient.
- **Plugin-like storage extensibility (without core rewrite):** a MountProvider boundary enabling Filestash-grade gateway behavior for SMB (server-mediated uploads, share links, and SMB WOPI using an app version string + locks) while preserving the existing S3-first behavior and remaining compatible with upstream-like standards.

### Market Context & Competitive Landscape

- **Differentiation hypothesis:** the combination of “self-host baseline + deterministic gates + contract-proofed storage compatibility + plugin-like mounts” is the primary differentiator, more than novel UI interaction patterns.
- **Validation need:** confirm with operators (self-host target) that these differentiators reduce deploy/debug time and storage/proxy incidents.

### Validation Approach

- Validate storage/proxy correctness via **CT-S3** (SeaweedFS as baseline profile) plus documented runbook checks mirroring the audience model.
- Validate SMB Mount v1 via deterministic Samba integration tests plus capability-gated UI flows.
- Validate operability via preflight/config validation plus smoke checklist (post-deploy, post-restore).
- Validate end-user critical flows via Chrome-only E2E (host-first) with retained artifacts.

### Risk Mitigation

- Avoid “big bang refactors”: keep MountProvider as an additive boundary; preserve S3 behavior.
- Keep innovation operationally safe: no-leak evidence policy, scoped scanners (`_bmad-output/**` text only), deterministic failure classes + next action hints.
- Treat “proxy-agnostic” as a contract: provide an Nginx baseline and document the key required behaviors (notably `/media` auth subrequest behavior and SigV4 header propagation, including optional STS token) so other reverse proxies can conform.

## Web App Specific Requirements

### Project-Type Overview
- Drive is a **SPA-like** application built with **Next.js** (hybrid framework), backed by a **Django/DRF** API.
- No SEO requirements (authenticated app). Public share links may exist but are not SEO-driven.
- No real-time requirements for v1.

### Technical Architecture Considerations
- The frontend must remain compatible with the existing backend contracts (REST APIs, auth flows, media access contracts) and the self-host packaging model (reverse proxy–agnostic edge behavior).
- Automation and deterministic gating remain first-class: changes should be verifiable via stable gate IDs and reproducible artifacts.

### Browser Matrix
- Supported browsers (v1 baseline): **Chrome, Edge, Firefox — last 2 major versions**.
- E2E automation remains **Chrome-only** for determinism, but the product requirement is multi-browser compatibility as defined above.

### Responsive Design
- The SPA must remain usable across typical viewport sizes without introducing regressions in core flows (browse, upload, preview, share links, WOPI entry points where enabled).
- Any responsive behavior expectations beyond “no regressions” are **TBD** and should be derived from current UI behavior and operator needs.

### Performance Targets
- Performance targets for v1 are **TBD** (no explicit numeric SLO provided yet).
- Baseline requirement: **no major performance regressions** in critical paths (navigation/listing, upload, preview, share link open, WOPI launch) as validated by the existing deterministic gates and smoke checks.

### SEO Strategy
- **No SEO** requirements for v1.
- Public pages (if any exist for share links) are not required to be SEO-optimized; focus remains on correctness, security, and operability.

### Accessibility Level
- **WCAG 2.1 AA compatibility (no regressions)** is the product baseline.
- Formal conformance audits/claims (RGAA/WCAG) remain **operator-owned** and deployment-context dependent.

### Implementation Considerations
- Prefer stable selectors and UI patterns that support deterministic automation (Chrome-only E2E) without compromising multi-browser support.
- Avoid introducing UI-only features that require real-time infrastructure in v1.

## Functional Requirements

### Identity, Access & Policy
- FR1: Users can authenticate via an external OIDC Identity Provider (bring-your-own).
- FR2: Operators can use `DRIVE_PUBLIC_URL` as the default basis for public-facing redirect/origin configuration, and can explicitly configure additional allowed redirect hosts/URIs when required by their IdP setup.
- FR3: The system can enforce application access and capability policies via an entitlements mechanism (e.g., can_access, can_upload).
- FR4: Integrators can enable Drive as a Resource Server and call External API routes permitted by configuration.
- FR5: Operators can restrict which External API endpoints/actions are exposed.

### Core File Experience (S3-backed baseline)
- FR6: Authenticated users can browse their workspaces and navigate folders.
- FR7: Users can create folders.
- FR8: Users can upload files to S3-backed storage via a browser-compatible upload flow.
- FR9: Users can download files.
- FR10: Users can preview supported files through the standard preview flow.
- FR11: Users can recover from common operational failures with clear, actionable feedback and safe diagnostics (no secrets), including at least: interrupted uploads, expired upload authorization, temporary storage unavailability, upload denied by policy/entitlements, and proxy/media access authorization failures.
- FR12: Operators can configure upload part sizing/chunk sizing for large uploads (S3 multipart and MountProvider uploads where applicable), with documented defaults and limits, **per-backend and per-mount where applicable**.

### Mounts (MountProvider Framework)
- FR13: Operators can configure MountProvider-based mounts with a stable `mount_id`, display name, provider type, and provider-specific non-secret connection parameters.
- FR14: Operators can enable/disable mounts without changing existing S3-backed behaviors.
- FR15: Users can discover available mounts and their capabilities via an API and a UI entry point.
- FR16: Users can browse a mount (list directories and view file/folder metadata) with deterministic ordering and pagination/limits.
- FR17: Users can download a mount file via backend-mediated streaming.
- FR18: Users can upload to a mount via backend-mediated streaming (large-file capable).
- FR19: Users can preview mount files when supported, with explicit capability-driven behavior when not supported.
- FR20: The system can enforce mount capability gating so unavailable actions are hidden/disabled (no dead buttons).
- FR21: The system can support at least one MountProvider implementation in v1 (SMB as the initial provider) without rewriting the S3-first core behavior.

### SMB Mount Configuration (Provider-Specific)
- FR22: Operators can configure an SMB mount with explicit connection parameters including (at minimum): `server` (host/IP), `share`, `port` (defaultable), `domain/workgroup` (optional), `username`, and a secret reference for the password (e.g., `password_secret_ref` and/or `password_secret_path`, reference only—not the secret value); plus optional SMB-specific settings such as `base_path` (share subpath) and connection timeouts.

### Mount Secrets (Transverse MountProvider Capability)
- FR23: Operators can reference secrets from mount configuration (e.g., `password_secret_ref`) rather than storing secret material in the database.
- FR24: The system can resolve mount secrets at runtime from operator-managed secret sources (e.g., env/file-backed secrets) without exposing secret values in APIs, logs, or generated artifacts.
- FR25: The system can enforce that secret values are never returned via any API; secret fields are reference-only (or write-only if an admin API/UI exists).
- FR26: If both secret reference mechanisms are supported (e.g., secret ref and secret path), the system can guarantee deterministic resolution precedence and document it.
- FR27: The system can support secret rotation without restarting the backend: when the referenced secret value changes, subsequent mount operations use the updated credentials within a bounded, operator-configurable time (at latest on the next new connection/session).
- FR28: The system can ensure mount connection/session reuse is safe across secret rotation and does not reuse stale credentials after a secret change; in-flight failures must not leak secret material.

### Share Links
- FR29: Users can create share links for S3-backed files and folders according to Drive’s sharing model.
- FR30: Users can create share links for MountProvider-backed resources identified by `(mount_id, path)`, with the explicit accepted constraint that links may break if the underlying target is renamed/moved/deleted out-of-band.
- FR31: Share link access can be enforced by token, without requiring an authenticated session (when configured as public).
- FR32: For MountProvider share links, the system can enforce deterministic and clean error semantics (no stacktraces):
  - unknown/invalid token returns `404`
  - valid/known token with missing target returns `410`
- FR33: The system can provide clear behavior when mount targets change out-of-band (no silent failures).

### WOPI / Collabora
- FR34: The system can expose WOPI actions only when enabled by explicit capability/prerequisites per storage backend (core S3 vs MountProvider-based mounts).
- FR35: If core S3 backend prerequisites (e.g., bucket versioning) are not met, the system can disable WOPI for that backend and provide operator-facing guidance (message + documentation reference).
- FR36: For MountProvider-based WOPI, the system can enforce an application-level version string and lock semantics (TTL, release, conflict handling).
- FR37: Users can launch WOPI editing for eligible files through a reverse-proxy-compatible flow.
- FR38: The system can enforce WOPI host allowlist inputs derived from `DRIVE_PUBLIC_URL`.
- FR39: The system can save WOPI edits back to the underlying storage backend through the supported write pipeline.

### Self-host Packaging & Edge Contracts
- FR40: Operators can set a canonical public base URL (`DRIVE_PUBLIC_URL`) and derive public-facing URLs consistently from it.
- FR41: Operators can deploy Drive behind a user-managed reverse proxy, using an Nginx reference configuration or an equivalent proxy-agnostic contract.
- FR42: The system can support the media access flow via an edge proxy auth subrequest pattern (e.g., `/media` auth subrequest) and preserve SigV4 headers returned by the media-auth endpoint when proxying media requests to S3 (e.g., `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`, and optionally `X-Amz-Security-Token`).
- FR43: Operators can follow documented procedures for backup/restore (DB + object storage + any locally-managed dev/test IdP fixtures if applicable) and validate with a post-restore smoke checklist.
- FR44: Operators can follow documented upgrade/rollback procedures and validate with a smoke checklist.

### Storage Correctness (Contract-first)
- FR45: Developers/CI can run Drive-integrated S3 contract tests with explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER).
- FR46: Contract test reports can capture safe evidence (status codes, request_id, hashes) without leaking credentials or sensitive paths/keys.
- FR47: The project can support a baseline S3-compatible provider profile in v1 (SeaweedFS as blocking profile) and encode expectations as repeatable tests and runbook checks.

### Deterministic Checks, Artifacts & Optional Strict Mirror
- FR48: Developers/CI can execute checks via stable, documented entrypoints (Make targets or equivalent wrappers).
- FR49: Checks can produce deterministic artifacts (machine-readable + human-readable) under `_bmad-output/implementation-artifacts/` when needed for troubleshooting.
- FR50: The system can classify failures with stable `failure_class` values and provide a `next_action_hint`.
- FR51 (optional/future): The project can compute a fingerprint from a canonical subset and embed it into issue/PR bodies.
- FR52 (optional/future): The system can detect and block strict-mirror drift (missing/mismatched fingerprints or template divergence).
- FR53: The system can enforce no-leak as a global requirement for APIs/logs/artifacts (not limited to scanned outputs).
- FR54: The system can limit automated scanning scope to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) to reduce false positives.

## Non-Functional Requirements

### Performance & Efficiency
- NFR1: Backend-mediated transfers (MountProvider downloads/uploads, WOPI save flows) shall be streaming and shall not require buffering entire file contents in memory, across v1-supported file sizes. **Verified via:** `backend.tests` + `mounts.integration.smb` (streaming contract) and retained failure artifacts.
- NFR2: Default upload size limits and large-upload behaviors (including multipart/part sizing) shall be documented (including defaults and min/max limits) and operator-configurable per backend and per mount where applicable. **Verified via:** `backend.tests` (config validation) + documented runbook checks.

### Reliability & Recoverability
- NFR3: The system shall provide deterministic, actionable failure reporting for automated checks and contract tests (stable `failure_class` + `next_action_hint`) and include both fields in reproducible artifacts for failing executions. **Verified via:** `backend.tests` and CI artifact retention on failures.
- NFR4: Backup/restore and upgrade/rollback procedures shall be documented and include a deterministic post-action smoke checklist (login, browse, upload, and media access via `media-auth`) executed after restore/upgrade actions. **Verified via:** runbook execution + `e2e.chrome` smoke flow and/or scripted smoke checklist artifacts.

### Security & Privacy
- NFR5: No-leak is enforced globally: secrets, credentials, and sensitive paths/keys shall not appear in API responses, logs, or generated artifacts (including on connection/auth failures). **Verified via:** CI + targeted tests for redaction/no-logging; any automated scanning should be scoped to `_bmad-output/**` text artifacts.
- NFR6: Automated no-leak scanning shall be limited to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) to reduce false positives while preserving the global no-leak requirement. **Verified via:** CI configuration + occasional local runs when producing shareable artifacts.
- NFR7: Production deployments shall support HTTPS for the public entry point (`DRIVE_PUBLIC_URL`) with no mixed TLS modes. **Verified via:** deployment docs + smoke checklist runbook and proxy configuration checks.

### Accessibility
- NFR8: The product shall maintain WCAG 2.1 AA compatibility with a “no regressions” policy across v1 work (including mounts and WOPI entry points when enabled) and must not introduce new serious/critical violations in the automated accessibility checks for the scoped flows. **Verified via:** `e2e.chrome` + automated accessibility checks (axe-based) with retained artifacts.

### Compatibility & Integration
- NFR9: The system shall remain compatible with a bring-your-own external OIDC IdP, including operator-configurable redirect allowances when required by the IdP configuration, and must support a successful login smoke flow when configured. **Verified via:** `backend.tests` (config validation) + end-to-end login smoke in `e2e.chrome`.
- NFR10: Reverse-proxy behavior shall be proxy-agnostic by contract (Nginx as a reference), including the `/media` auth subrequest contract and SigV4 header propagation (including optional STS token) for media proxying. **Verified via:** `s3.contracts.seaweedfs` + documented proxy contract smoke checklist.
