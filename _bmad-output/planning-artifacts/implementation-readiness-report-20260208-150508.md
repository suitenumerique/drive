---
stepsCompleted: [1, 2, 3, 4, 5, 6]
project_name: drive
date: '2026-02-08T15:05:08Z'
includedDocuments:
  prd: _bmad-output/planning-artifacts/prd.md
  architecture: _bmad-output/planning-artifacts/architecture.md
  epics_and_stories: _bmad-output/planning-artifacts/epics.md
  ux_design: _bmad-output/planning-artifacts/ux-design-specification.md
supportingDocuments:
  - _bmad-output/planning-artifacts/validation-report-prd-20260203-234119.md
  - _bmad-output/planning-artifacts/validation-report-architecture-20260205-130922.md
  - _bmad-output/planning-artifacts/validation-report-ux-20260204-222522.md
excludedDocuments:
  - _bmad-output/planning-artifacts/prd.validation-report.md.old
notes:
  ux_source_of_truth: ux-design-specification.md (draft excluded)
---

# Implementation Readiness Assessment Report

**Date:** 2026-02-08
**Project:** drive

## Step 1 — Document Discovery (Inventory)

### PRD

- Whole (selected): `_bmad-output/planning-artifacts/prd.md`
- Supporting (kept): `_bmad-output/planning-artifacts/validation-report-prd-20260203-234119.md`
- Excluded (do not load): `_bmad-output/planning-artifacts/prd.validation-report.md.old`
- Sharded: none found

### Architecture

- Whole (selected): `_bmad-output/planning-artifacts/architecture.md`
- Supporting (kept): `_bmad-output/planning-artifacts/validation-report-architecture-20260205-130922.md`
- Sharded: none found

### Epics & Stories

- Whole (selected): `_bmad-output/planning-artifacts/epics.md`
- Sharded: none found

### UX Design

- Whole (selected source of truth): `_bmad-output/planning-artifacts/ux-design-specification.md`
- Supporting (kept): `_bmad-output/planning-artifacts/validation-report-ux-20260204-222522.md`
- Supporting (not selected): `_bmad-output/planning-artifacts/ux-design-specification.step-10.draft.md`
- Supporting (not selected): `_bmad-output/planning-artifacts/ux-design-directions.html`
- Sharded: none found

## PRD Analysis

### Functional Requirements Extracted

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
  - unknown/invalid token returns `404`
  - valid/known token with missing target returns `410`
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

Total FRs: 54

### Non-Functional Requirements Extracted

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

Total NFRs: 10

### Additional Requirements Extracted (Constraints / Assumptions / Non-FR/NFR)

- Repo scope: work happens only in `Apoze/drive` (no upstream interactions).
- Evidence/no-leak: reports/artifacts must avoid secrets, credentials, and raw sensitive paths/keys.
- E2E: Chrome-only for determinism (host-first), artifacts retained; product requirement remains multi-browser compatibility (Chrome/Edge/Firefox last 2 majors).
- v1 strategy: self-host baseline (operability + storage correctness + extensibility), not a minimal slice.
- Mount v1 accepted constraints:
  - No synchronization between SMB and S3
  - Global mount permissions (single service account), no per-path SMB RBAC
  - Share links are path-based and may break on out-of-band SMB path changes
  - Share link error semantics: `404` invalid/unknown token; `410` valid token but missing target
- Compliance context (operator-owned, deployment-dependent): procurement constraints, restricted environments (air-gapped/mirroring), transparency/auditability expectations.
- Performance targets: numeric SLOs are TBD; baseline requirement is “no major regressions” in critical paths validated by existing gates/smoke.

### PRD Completeness Assessment

- Requirement inventory is complete and consistently numbered (FR1–FR54, NFR1–NFR10).
- Most requirements are measurable via explicit “Verified via” hints (gates, CT-S3, E2E, runbooks).
- A few statements remain open-ended/TBD (e.g., performance numeric targets; some implementation naming in success criteria), but do not block traceability as long as epics/stories remain contract-focused.

## Epic Coverage Validation

### Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| --------- | --------------- | ------------ | -------- |
| FR1 | Users can authenticate via an external OIDC Identity Provider (bring-your-own). | Epic 3 - BYO OIDC authentication | ✓ Covered |
| FR2 | Operators can use `DRIVE_PUBLIC_URL` as the default basis for public-facing redirect/origin configuration, and can explicitly configure additional allowed redirect hosts/URIs when required by their IdP setup. | Epic 1 - `DRIVE_PUBLIC_URL` basis + explicit redirect allowlists | ✓ Covered |
| FR3 | The system can enforce application access and capability policies via an entitlements mechanism (e.g., can_access, can_upload). | Epic 3 - entitlements-driven access/capabilities | ✓ Covered |
| FR4 | Integrators can enable Drive as a Resource Server and call External API routes permitted by configuration. | Epic 3 - resource server enablement for external API routes | ✓ Covered |
| FR5 | Operators can restrict which External API endpoints/actions are exposed. | Epic 3 - restrict exposed external API endpoints/actions | ✓ Covered |
| FR6 | Authenticated users can browse their workspaces and navigate folders. | Epic 4 - browse workspaces/folders | ✓ Covered |
| FR7 | Users can create folders. | Epic 4 - create folders | ✓ Covered |
| FR8 | Users can upload files to S3-backed storage via a browser-compatible upload flow. | Epic 4 - S3 browser upload flow | ✓ Covered |
| FR9 | Users can download files. | Epic 4 - download files | ✓ Covered |
| FR10 | Users can preview supported files through the standard preview flow. | Epic 4 - preview supported files | ✓ Covered |
| FR11 | Users can recover from common operational failures with clear, actionable feedback and safe diagnostics (no secrets), including at least: interrupted uploads, expired upload authorization, temporary storage unavailability, upload denied by policy/entitlements, and proxy/media access authorization failures. | Epic 5 - actionable recovery from operational failures (no-leak) | ✓ Covered |
| FR12 | Operators can configure upload part sizing/chunk sizing for large uploads (S3 multipart and MountProvider uploads where applicable), with documented defaults and limits, **per-backend and per-mount where applicable**. | Epic 4 - configurable chunk/part sizing per backend/mount | ✓ Covered |
| FR13 | Operators can configure MountProvider-based mounts with a stable `mount_id`, display name, provider type, and provider-specific non-secret connection parameters. | Epic 7 - configure mounts (`mount_id`, provider, params) | ✓ Covered |
| FR14 | Operators can enable/disable mounts without changing existing S3-backed behaviors. | Epic 7 - enable/disable mounts without changing S3 behavior | ✓ Covered |
| FR15 | Users can discover available mounts and their capabilities via an API and a UI entry point. | Epic 7 - discover mounts + capabilities (API + UI entry) | ✓ Covered |
| FR16 | Users can browse a mount (list directories and view file/folder metadata) with deterministic ordering and pagination/limits. | Epic 7 - browse mount with deterministic ordering + pagination | ✓ Covered |
| FR17 | Users can download a mount file via backend-mediated streaming. | Epic 9 - download mount file via backend streaming | ✓ Covered |
| FR18 | Users can upload to a mount via backend-mediated streaming (large-file capable). | Epic 9 - upload to mount via backend streaming (large-file capable) | ✓ Covered |
| FR19 | Users can preview mount files when supported, with explicit capability-driven behavior when not supported. | Epic 9 - preview mount files when supported (capability-driven) | ✓ Covered |
| FR20 | The system can enforce mount capability gating so unavailable actions are hidden/disabled (no dead buttons). | Epic 7 - capability gating (no dead actions) | ✓ Covered |
| FR21 | The system can support at least one MountProvider implementation in v1 (SMB as the initial provider) without rewriting the S3-first core behavior. | Epic 7 - MountProvider boundary supports SMB v1 without rewriting S3 core | ✓ Covered |
| FR22 | Operators can configure an SMB mount with explicit connection parameters including (at minimum): `server` (host/IP), `share`, `port` (defaultable), `domain/workgroup` (optional), `username`, and a secret reference for the password (e.g., `password_secret_ref` and/or `password_secret_path`, reference only—not the secret value); plus optional SMB-specific settings such as `base_path` (share subpath) and connection timeouts. | Epic 9 - SMB mount configuration parameters | ✓ Covered |
| FR23 | Operators can reference secrets from mount configuration (e.g., `password_secret_ref`) rather than storing secret material in the database. | Epic 8 - mount secrets are references (no secret material in DB) | ✓ Covered |
| FR24 | The system can resolve mount secrets at runtime from operator-managed secret sources (e.g., env/file-backed secrets) without exposing secret values in APIs, logs, or generated artifacts. | Epic 8 - runtime secret resolution from operator-managed sources (no leak) | ✓ Covered |
| FR25 | The system can enforce that secret values are never returned via any API; secret fields are reference-only (or write-only if an admin API/UI exists). | Epic 8 - enforce secrets never returned via API | ✓ Covered |
| FR26 | If both secret reference mechanisms are supported (e.g., secret ref and secret path), the system can guarantee deterministic resolution precedence and document it. | Epic 8 - deterministic secret resolution precedence | ✓ Covered |
| FR27 | The system can support secret rotation without restarting the backend: when the referenced secret value changes, subsequent mount operations use the updated credentials within a bounded, operator-configurable time (at latest on the next new connection/session). | Epic 8 - secret rotation without restart (bounded time) | ✓ Covered |
| FR28 | The system can ensure mount connection/session reuse is safe across secret rotation and does not reuse stale credentials after a secret change; in-flight failures must not leak secret material. | Epic 8 - safe session reuse across rotation; no secret leaks on failures | ✓ Covered |
| FR29 | Users can create share links for S3-backed files and folders according to Drive’s sharing model. | Epic 6 - share links for S3 files/folders | ✓ Covered |
| FR30 | Users can create share links for MountProvider-backed resources identified by `(mount_id, path)`, with the explicit accepted constraint that links may break if the underlying target is renamed/moved/deleted out-of-band. | Epic 6 - share links for MountProvider resources `(mount_id, path)` | ✓ Covered |
| FR31 | Share link access can be enforced by token, without requiring an authenticated session (when configured as public). | Epic 6 - token-enforced access without authenticated session (when public) | ✓ Covered |
| FR32 | For MountProvider share links, the system can enforce deterministic and clean error semantics (no stacktraces): - unknown/invalid token returns `404` - valid/known token with missing target returns `410` | Epic 6 - deterministic MountProvider share-link error semantics (no stacktraces) | ✓ Covered |
| FR33 | The system can provide clear behavior when mount targets change out-of-band (no silent failures). | Epic 6 - explicit behavior for out-of-band mount target changes | ✓ Covered |
| FR34 | The system can expose WOPI actions only when enabled by explicit capability/prerequisites per storage backend (core S3 vs MountProvider-based mounts). | Epic 10 - expose WOPI actions only when capability/prereqs met per backend | ✓ Covered |
| FR35 | If core S3 backend prerequisites (e.g., bucket versioning) are not met, the system can disable WOPI for that backend and provide operator-facing guidance (message + documentation reference). | Epic 10 - disable WOPI on S3 prereq failure; operator guidance | ✓ Covered |
| FR36 | For MountProvider-based WOPI, the system can enforce an application-level version string and lock semantics (TTL, release, conflict handling). | Epic 10 - mount WOPI version string + lock semantics (TTL/release/conflicts) | ✓ Covered |
| FR37 | Users can launch WOPI editing for eligible files through a reverse-proxy-compatible flow. | Epic 10 - launch WOPI editing via reverse-proxy-compatible flow | ✓ Covered |
| FR38 | The system can enforce WOPI host allowlist inputs derived from `DRIVE_PUBLIC_URL`. | Epic 10 - WOPI host allowlist derived from `DRIVE_PUBLIC_URL` | ✓ Covered |
| FR39 | The system can save WOPI edits back to the underlying storage backend through the supported write pipeline. | Epic 10 - save WOPI edits back to underlying storage backend | ✓ Covered |
| FR40 | Operators can set a canonical public base URL (`DRIVE_PUBLIC_URL`) and derive public-facing URLs consistently from it. | Epic 1 - canonical public base URL derivations from `DRIVE_PUBLIC_URL` | ✓ Covered |
| FR41 | Operators can deploy Drive behind a user-managed reverse proxy, using an Nginx reference configuration or an equivalent proxy-agnostic contract. | Epic 2 - deploy behind user-managed reverse proxy (Nginx reference/contract) | ✓ Covered |
| FR42 | The system can support the media access flow via an edge proxy auth subrequest pattern (e.g., `/media` auth subrequest) and preserve SigV4 headers returned by the media-auth endpoint when proxying media requests to S3 (e.g., `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`, and optionally `X-Amz-Security-Token`). | Epic 2 - `/media` auth subrequest + SigV4 header propagation via edge proxy | ✓ Covered |
| FR43 | Operators can follow documented procedures for backup/restore (DB + object storage + any locally-managed dev/test IdP fixtures if applicable) and validate with a post-restore smoke checklist. | Epic 2 - documented backup/restore + post-restore smoke checklist | ✓ Covered |
| FR44 | Operators can follow documented upgrade/rollback procedures and validate with a smoke checklist. | Epic 2 - documented upgrade/rollback + smoke checklist | ✓ Covered |
| FR45 | Developers/CI can run Drive-integrated S3 contract tests with explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER). | Epic 11 - run Drive-integrated S3 contract tests with explicit audiences | ✓ Covered |
| FR46 | Contract test reports can capture safe evidence (status codes, request_id, hashes) without leaking credentials or sensitive paths/keys. | Epic 11 - CT-S3 reports capture safe evidence without leaks | ✓ Covered |
| FR47 | The project can support a baseline S3-compatible provider profile in v1 (SeaweedFS as blocking profile) and encode expectations as repeatable tests and runbook checks. | Epic 11 - SeaweedFS blocking baseline profile encoded as repeatable tests/checks | ✓ Covered |
| FR48 | Developers/CI can execute checks via stable `gate_id`s (resolved to existing Makefile targets/commands by a gates runner). | Epic 12 - stable `gate_id`s executed via gates runner | ✓ Covered |
| FR49 | Each gate execution can produce deterministic artifacts (machine-readable + human-readable) under `_bmad-output/implementation-artifacts/`. | Epic 12 - deterministic artifacts under `_bmad-output/implementation-artifacts/` | ✓ Covered |
| FR50 | The system can classify failures with stable `failure_class` values and provide a `next_action_hint`. | Epic 12 - stable `failure_class` + `next_action_hint` | ✓ Covered |
| FR51 | The project can compute a registry fingerprint (B+) from the canonical subset and embed it into issue/PR bodies. | Epic 12 - registry fingerprint (B+) embedded in issue/PR bodies | ✓ Covered |
| FR52 | The system can detect and block strict-mirror drift (missing/mismatched fingerprints or template divergence). | Epic 12 - detect/block strict-mirror drift | ✓ Covered |
| FR53 | The system can enforce no-leak as a global requirement for APIs/logs/artifacts (not limited to scanned outputs). | Epic 12 - enforce no-leak globally for APIs/logs/artifacts | ✓ Covered |
| FR54 | The system can limit automated scanning scope to `_bmad-output/**` text artifacts (`.md`, `.json`, `.txt`) to reduce false positives. | Epic 12 - limit automated scanning scope to `_bmad-output/**` text artifacts | ✓ Covered |

### Missing Requirements

- None (all PRD FRs are mapped in the epics FR coverage map).

### Coverage Statistics

- Total PRD FRs: 54
- FRs covered in epics: 54
- Coverage percentage: 100%

## UX Alignment Assessment

### UX Document Status

- Found (selected source of truth): `_bmad-output/planning-artifacts/ux-design-specification.md`

### Alignment Issues

- UX expectation: “upload queue/progress remains visible cross-folder” is explicit in UX, but not explicitly stated as an FR/NFR in the PRD nor as an explicit AC in the Epics/Stories (risk: implementation may deliver per-folder-only feedback unless clarified).
- UX includes conceptual operator surfaces for Mount secrets (validate/refresh/status UI patterns). PRD/Architecture allow operator-first flows but do not mandate an in-app mount configuration UI; confirm whether this is intended as v1 scope or documented as “conceptual / future”.

### Warnings

- None of the above appears to contradict the PRD/Architecture; they are primarily “scope clarity” items. If treated as v1 requirements, they should be promoted into explicit story acceptance criteria to avoid drift.

## Epic Quality Review (create-epics-and-stories best practices)

### 🔴 Critical Violations

1) Epic independence violation (Epic 6 → Epic 7 forward dependency)
- Epic 6 includes MountProvider share links (Story 6.3, Story 6.4), but the MountProvider framework is Epic 7 (and provider implementation is Epic 9).
- This violates the “Epic N cannot require Epic N+1 to work” rule: Epic 6 cannot deliver its full scope without future epics.
- Recommended remediation (choose one):
  - Move MountProvider share link stories (6.3/6.4) into Epic 7 (framework) or Epic 9 (SMB provider) as provider-backed deliverables, and keep Epic 6 focused on S3 share links only; or
  - Renumber/reorder epics so MountProvider framework (current Epic 7) precedes MountProvider share links; or
  - Split into two epics: “S3 Share Links” and “Mount Share Links” (after MountProvider exists).

2) Within-epic forward dependency (Epic 3 external API allowlist)
- Story 3.3 (“external API/resource server”) asserts allowlisting behavior, while Story 3.4 defines the allowlist model/validation.
- This is a forward dependency within the same epic (3.3 implicitly depends on 3.4).
- Recommended remediation: reorder as 3.4 then 3.3, or merge allowlist model into 3.3 and keep 3.4 as refinement only.

### 🟠 Major Issues

- Epic 11 and Epic 12 are “developer/operator value” epics but are close to being framed as technical milestones; ensure every story outcome is consistently phrased as user value for a named persona (developer/CI/operator) and includes concrete acceptance checks (already mostly true, but keep consistent).

### 🟡 Minor Concerns

- Some acceptance criteria use “implementation-defined/where applicable” language (e.g., temp upload finalize semantics, range support), which is acceptable but should be paired with explicit deterministic test strategy/gate references in implementation planning to avoid ambiguity during execution.

## Summary and Recommendations

### Overall Readiness Status

NOT READY

### Critical Issues Requiring Immediate Action

1) Epic ordering/independence defect
- Epic 6 (Share Links) includes mount share link stories that require Epic 7 (MountProvider framework) and Epic 9 (SMB provider) to exist.

2) Within-epic forward dependency defect
- Epic 3 Story 3.3 relies on allowlisting that is only defined in Epic 3 Story 3.4.

### Recommended Next Steps

1. Fix Epic 6 scope/order: keep Epic 6 strictly S3 share links, and move mount share link stories to an epic that comes after MountProvider exists (Epic 7/9), or renumber epics so MountProvider precedes mount share links.
2. Fix Epic 3 story sequencing: reorder Story 3.4 before Story 3.3 (or merge), so no story depends on a future story within the same epic.
3. Decide scope clarity items from UX:
   - Promote “upload queue/progress visible cross-folder” to an explicit story AC (if required for v1), or explicitly mark it as non-goal.
   - Decide whether mount secrets “validate/refresh/status” UI patterns are v1 deliverables or conceptual/future; align epics accordingly.

### Final Note

This assessment found 2 critical structural defects (epic/story dependency ordering) plus 2 UX scope-clarity alignment items. Address the critical issues before proceeding to implementation to avoid agent drift and rework; FR coverage mapping is complete (54/54).
