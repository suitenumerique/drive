# Story 2.1: Docker-first edge contract documentation + configuration validation + smoke checks

Status: ready-for-dev

Story Key: `2-1-docker-first-edge-contract-documentation-configuration-validation-smoke-checks`
Generated: 2026-02-08

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want a Docker-first v1 deployment contract (proxy-agnostic) with documentation, configuration validation, and testable smoke checks,
so that I can deploy reliably behind my reverse proxy without drifting into Kubernetes/Helm scope in v1.

## Acceptance Criteria

1. **Given** v1 scope is Docker-first  
   **When** I read the self-host documentation/runbooks  
   **Then** Docker (single-machine / compose) is the baseline, and Kubernetes/Helm is explicitly “as-is reference-only” (no v1 improvements, no v1 K8s gates).

2. **Given** I deploy behind any reverse proxy (not necessarily Nginx)  
   **When** I consult the documentation  
   **Then** the required edge contract is described in proxy-agnostic terms (Nginx is a reference implementation only).

3. **Given** configuration preflight/validation runs  
   **When** it evaluates reverse-proxy/media-related configuration inputs  
   **Then** it validates the inputs deterministically (without attempting to “inspect” the actual proxy) and outputs an operator-facing checklist and/or guidance for verifying the edge contract in the deployed environment.

4. **Given** operator smoke checks are executed (via documented steps and/or optional smoke endpoint(s))  
   **When** they report results for media/S3 edge paths  
   **Then** the results reflect the audience model (`INTERNAL_PROXY` vs `EXTERNAL_BROWSER`) with safe evidence only (no-leak).

5. **Given** configuration is missing/unsafe/inconsistent for the current deployment mode  
   **When** preflight/validation runs  
   **Then** it fails early with deterministic `failure_class` + `next_action_hint`, and remains no-leak.

## Tasks / Subtasks

- [ ] **Document Docker-first self-host contract** (AC: 1, 2)
  - [ ] Create `docs/selfhost/README.md` (entry point; v1 scope; Docker-first; K8s reference-only).
  - [ ] Create `docs/selfhost/edge-contract.md` describing the `/media` contract in proxy-agnostic terms:
    - [ ] required routes (`/media/`, `/media/preview/`, `/media-auth` subrequest target),
    - [ ] required forwarded SigV4 headers (incl. optional `X-Amz-Security-Token`),
    - [ ] signed host invariants (`connect_url` vs `signed_host` pattern),
    - [ ] no-leak and logging guidance (do not log SigV4 headers).
  - [ ] Add/adjust links from `docs/installation/README.md` (and optionally root `README.md`) pointing to `docs/selfhost/`.

- [ ] **Extend deterministic config preflight** (AC: 3, 5)
  - [ ] Extend `src/backend/core/management/commands/config_preflight.py` to validate reverse-proxy/media-related configuration inputs:
    - [ ] `AWS_S3_ENDPOINT_URL` (required) is a valid absolute URL (no userinfo; scheme allowlist).
    - [ ] `AWS_S3_DOMAIN_REPLACE` (optional) is a valid URL when set; document how it maps to EXTERNAL_BROWSER signing.
    - [ ] Emit deterministic `errors[]` with `field`, `failure_class`, `next_action_hint` (no-leak).
    - [ ] Emit `manual_checks[]` (or similar) that prints the edge-contract checklist without inspecting the live proxy.
  - [ ] Add failure classes consistent with repo conventions (prefer `config.*` namespace) and keep them stable.

- [ ] **Docker-first smoke checklist** (AC: 4)
  - [ ] Create `docs/selfhost/smoke-checklist.md` with deterministic steps and expected outcomes:
    - [ ] login (BYO OIDC in prod; Keycloak only as dev fixture),
    - [ ] browse workspace/folder,
    - [ ] upload (EXTERNAL_BROWSER),
    - [ ] media access via `/media` (INTERNAL_PROXY),
    - [ ] failure modes mapped to `failure_class` + safe evidence + next actions.
  - [ ] Ensure the checklist explicitly distinguishes INTERNAL_PROXY vs EXTERNAL_BROWSER breakpoints.

- [ ] **Tests** (AC: 3, 5)
  - [ ] Extend `src/backend/core/tests/commands/test_config_preflight.py` to cover new validation branches and failure classes.
  - [ ] Add at least one regression test ensuring preflight output remains deterministic (sorted keys; stable field names).

- [ ] **(Optional) Operator-facing quick health endpoint** (AC: 4)
  - [ ] If implemented, keep it operator-only and no-leak; output audience-aware status with safe evidence only.

## Dev Notes

### Scope (this story)

- Add **proxy-agnostic** documentation for the `/media` edge contract (Nginx as a reference implementation only).
- Extend **deterministic config preflight/validation** to cover reverse-proxy + media/S3 inputs, and emit `failure_class` + `next_action_hint` (no-leak).
- Provide a **Docker-first smoke checklist** (and/or optional smoke endpoint/command) that reports **INTERNAL_PROXY vs EXTERNAL_BROWSER** status with safe evidence only.
- Explicitly keep **Kubernetes/Helm “as-is reference-only”** for v1 (no new guarantees, no new K8s gates).

### Existing repo touchpoints (high-signal)

- Backend media-auth endpoint (Nginx auth subrequest target): `src/backend/core/api/viewsets.py` (`media_auth` action).
- SigV4 header generation for `/media` proxying: `src/backend/core/api/utils.py#generate_s3_authorization_headers`.
- Existing deterministic preflight command (currently only `DRIVE_PUBLIC_URL`): `src/backend/core/management/commands/config_preflight.py`.
- Existing preflight tests: `src/backend/core/tests/commands/test_config_preflight.py` and URL normalization errors in `src/backend/core/utils/public_url.py`.
- Nginx reference configs (Docker dev/prod): `docker/files/development/etc/nginx/conf.d/default.conf`, `docker/files/production/etc/nginx/conf.d/default.conf`.
- Nginx template for hosted deployments: `src/nginx/servers.conf.erb`.
- Reference-only Kubernetes ingress knobs (do not harden in v1): `src/helm/drive/**` and `docs/examples/helm/**`.
- Failure taxonomy conventions: `docs/failure-class-glossary.md`.
- UX operator diagnostics intent (audience-aware, no-leak safe evidence): `_bmad-output/planning-artifacts/ux-design-specification.step-10.draft.md` (Journey J5).
- Product “Self-host Operator” journey: `_bmad-output/planning-artifacts/prd.md` (Journey 1).

### Edge contract overview (proxy-agnostic)

The `/media` flow is an **edge-mediated** S3 access pattern:

1. **Client → Edge**: `GET /media/...` (or `/media/preview/...`).
2. **Edge → Backend (subrequest)**: `GET /api/v1.0/items/media-auth/` (auth subrequest) with `X-Original-URL` + `X-Original-Method` so the backend can derive the target object key safely.
3. **Edge → Object storage**: only if backend subrequest returns 200; edge proxies to S3 using **SigV4 headers** returned by `media-auth`.

Critical invariants:

- The edge must forward all required SigV4 headers returned by `media-auth` (at minimum `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256`; and **optionally** `X-Amz-Security-Token` when session credentials are used; plus any other `x-amz-*` headers required by the chosen auth/signature strategy).
- The edge must preserve the **signed host** invariant for INTERNAL_PROXY: “signed host == Host used” (or use the documented `connect_url` vs `signed_host` technique where applicable).
- The edge contract must remain **no-leak** (do not log SigV4 headers; do not surface raw S3 keys/paths; only safe evidence like status codes, request_id, and hashes).

### Audience model to reflect in validation and smoke output

- `INTERNAL_PROXY`: backend/edge access to object storage (SigV4 via `/media-auth` and edge proxying).
- `EXTERNAL_BROWSER`: browser presigned upload access (signing may use `AWS_S3_DOMAIN_REPLACE`; CORS/public URL constraints derive from `DRIVE_PUBLIC_URL`).

### Known drifts / pitfalls to call out explicitly

- Docker configs currently reference **MinIO** (`compose.yaml`, `docker/files/**/default.conf`), while architecture context indicates a move toward a **SeaweedFS S3 gateway baseline**. Keep this story provider-agnostic; avoid locking docs/checks to one backend.
- Current Nginx reference config forwards only a subset of SigV4 headers; session-token setups will require forwarding `X-Amz-Security-Token` at minimum (address later if not in this story).

### Technical requirements (dev agent guardrails)

- **Deterministic outputs:** config validation and smoke artifacts must be stable (sorted keys, stable ordering, no timestamps inside evidence unless explicitly required).
- **No-leak by construction:** never output secrets, raw S3 keys/object paths, filenames, or credentials; evidence must be allow-listed (status codes, request_id, hashes).
- **Failure taxonomy:** emit `failure_class` + `next_action_hint` for every failure, using the repo glossary conventions (`domain.category.reason`).
- **Proxy-agnostic contract language:** docs must describe required behavior without “Nginx-only” assumptions; Nginx snippets are reference examples only.
- **No proxy inspection:** preflight/validation must validate configuration inputs and provide manual checks; it must not attempt to introspect a live reverse proxy.
- **K8s reference-only:** do not add new Kubernetes/Helm guarantees, gates, or “v1 hardened” claims; keep existing files as reference “as-is”.

### Architecture compliance (must align)

- Docker-first v1: place runbooks/docs under `docs/selfhost/` (planned architecture boundary) and link from existing install docs.
- Edge proxy: document `/media` auth subrequest + SigV4 header propagation as a hard contract; treat Nginx as the reference implementation only.
- Canonical public URL: config validation must continue to treat `DRIVE_PUBLIC_URL` as the source of truth for derived public surfaces; production enforces HTTPS (no mixed TLS modes).
- Deterministic delivery: any generated artifacts/reports should live under `_bmad-output/implementation-artifacts/` and remain safe for no-leak text scanning.

### Library/framework requirements

- Backend validation must be implemented as a Django management command (extend `config_preflight`) using standard library parsing (`urllib.parse`) and existing project utilities (reuse `core/utils/public_url.py` patterns).
- Do not introduce a new validation framework/library unless already present and justified.
- Documentation should live in `docs/` (English), and code/comments must remain English-only.

### Testing requirements

- Backend unit tests must cover new preflight validations and failure classes (extend `src/backend/core/tests/commands/test_config_preflight.py`).
- Where appropriate, add a lightweight smoke-level assertion for the `/items/media-auth/` contract (do not leak object keys; prefer request/response shape + header presence checks).
- Documentation changes must be verifiable via a deterministic “smoke checklist” run (at minimum: preflight command output + operator manual checks).

### Latest technical notes (web research)

- Nginx `auth_request` is the intended pattern for “authorize via subrequest, then proxy” flows; `auth_request_set` is used to copy subrequest response headers into variables for use in the main request (needed for SigV4 header propagation).
- Be explicit in docs that **headers returned by `media-auth`** must be forwarded to the S3 upstream request, and that logging must not capture SigV4 headers (no-leak).

### Project Structure Notes

- **Docs location:** create `docs/selfhost/` (per architecture “planned” boundary) for Docker-first runbooks and edge-contract documentation; link from `docs/installation/README.md` (and optionally root `README.md`) so operators discover it.
- **Backend validation location:** extend `src/backend/core/management/commands/config_preflight.py`; add/extend tests under `src/backend/core/tests/commands/test_config_preflight.py`.
- **Reference configs:** keep Nginx examples in existing locations (`docker/files/**/nginx/conf.d/default.conf`, `src/nginx/servers.conf.erb`). Do not reorganize in this story unless required for clarity.
- **Kubernetes files:** treat `src/helm/**` and `docs/examples/helm/**` as reference-only; avoid edits except to add clear “reference-only” wording if needed.
- **Known drift:** Docker baseline currently references MinIO (`compose.yaml`, `docker/files/**`) while architecture context indicates SeaweedFS baseline; document storage backend choices without hard-coding to one provider.

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 2.1 acceptance criteria; Epic 2 scope framing.
- `_bmad-output/planning-artifacts/prd.md` — “Journey 1 — Self-host Operator: bootstrap → config → deploy → smoke”.
- `_bmad-output/planning-artifacts/architecture.md` — “Infrastructure & Deployment”, “Complete Project Directory Structure”, “Requirements to Structure Mapping”.
- `_bmad-output/project-context.md` — non-negotiables (no-leak, capability-driven, Docker-first intent) + file pointers.
- `_bmad-output/planning-artifacts/ux-design-specification.step-10.draft.md` — Journey J5 (audience-aware diagnostics; safe evidence).
- `docs/failure-class-glossary.md` — deterministic `failure_class` conventions.
- Backend:
  - `src/backend/core/management/commands/config_preflight.py` (preflight output contract)
  - `src/backend/core/api/viewsets.py` (`/api/v1.0/items/media-auth/`)
  - `src/backend/core/api/utils.py` (SigV4 signing helpers)
- Proxy templates:
  - `docker/files/development/etc/nginx/conf.d/default.conf`
  - `docker/files/production/etc/nginx/conf.d/default.conf`
  - `src/nginx/servers.conf.erb`
- Packaging baseline (current dev stack inputs; note drift): `compose.yaml`, `env.d/development/common`
- Web reference (for doc correctness): Nginx `auth_request` module docs (`http://nginx.org/en/docs/http/ngx_http_auth_request_module.html`)

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created

### File List
