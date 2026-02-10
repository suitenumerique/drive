# Story 1.2: Separate allowlists for redirect URIs vs origins/hosts (derived from `DRIVE_PUBLIC_URL`)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

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

## Acceptance Criteria

1. **Given** `DRIVE_PUBLIC_URL` is valid **When** the system computes/validates allowlisted values **Then** the canonical values derived from `DRIVE_PUBLIC_URL` are always included by default.
2. **Given** the operator configures additional allowed redirect URIs **When** configuration preflight/validation runs **Then** each entry is an absolute URI (scheme + host + path), is validated deterministically (no wildcards, no ambiguous parsing), is normalized/deduplicated, and in production requires `https://` unless the dev-only insecure override is explicitly enabled.
3. **Given** the operator configures additional allowed origins/hosts (for origin/CORS/host checks where applicable) **When** configuration preflight/validation runs **Then** each entry is validated deterministically (host-only or origin form as applicable), contains no wildcards, is normalized/deduplicated, and in production requires HTTPS origins where an origin is used unless the dev-only insecure override is explicitly enabled.
4. **Given** any allowlisted entry is invalid or unsafe for the current deployment mode **When** configuration preflight/validation runs **Then** the system fails early with deterministic `failure_class` + `next_action_hint`, without leaking secrets or sensitive paths.
## Tasks / Subtasks

- [ ] Map existing settings to the new split model (AC: 1)
  - [ ] Identify how `lasuite.oidc_login` consumes `OIDC_REDIRECT_ALLOWED_HOSTS` / `OIDC_REDIRECT_REQUIRE_HTTPS` and where the “returnTo” (aka `OIDC_REDIRECT_FIELD_NAME`) validation occurs.
  - [ ] Inventory current origin/host allowlists used by Drive:
    - `ALLOWED_HOSTS` (Django),
    - `CORS_ALLOWED_ORIGINS` / `CORS_ALLOWED_ORIGIN_REGEXES`,
    - `CSRF_TRUSTED_ORIGINS`,
    - `SDK_CORS_ALLOWED_ORIGINS` (used by SDK relay preflight).
- [ ] Define new operator-facing allowlists (split by purpose) (AC: 1, 2, 3, 4)
  - [ ] Add settings for **additional redirect targets** (absolute URIs) vs **additional origins** (scheme+host+port only) vs **additional hosts** (hostnames only).
  - [ ] Keep backward compatibility: if legacy env vars exist (e.g., `OIDC_REDIRECT_ALLOWED_HOSTS`), merge them deterministically with the new derived/default values.
  - [ ] Ensure canonical derived values from `DRIVE_PUBLIC_URL` are always included.
- [ ] Implement deterministic validators/normalizers (AC: 2, 3, 4)
  - [ ] Redirect URI entries: absolute URI; no wildcards; deterministic parsing; normalized/deduped; enforce HTTPS in production posture unless dev override is enabled.
  - [ ] Origin entries: must be an origin (no path/query/fragment); no wildcards; normalized/deduped; enforce HTTPS origins in production posture unless dev override is enabled.
  - [ ] Host entries: hostname (optionally including explicit ports only if supported by the downstream consumer); no wildcards; normalized/deduped.
  - [ ] Fail fast with stable `failure_class` + `next_action_hint` (extend `docs/failure-class-glossary.md`).
- [ ] Wire into settings boot and consumers (AC: 1, 2, 3, 4)
  - [ ] In `src/backend/drive/settings.py:Base.post_setup`, compute the final derived allowlists and apply them to:
    - `OIDC_REDIRECT_ALLOWED_HOSTS` and `OIDC_REDIRECT_REQUIRE_HTTPS` (for OIDC “returnTo” behavior),
    - `SDK_CORS_ALLOWED_ORIGINS` (SDK relay),
    - optionally `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS` (only if aligned with current deployment expectations).
  - [ ] Keep `ALLOWED_HOSTS` explicit in Production unless there is a clear migration strategy; if derived host is appended, do it deterministically and document it.
- [ ] Add tests + docs (AC: 2, 3, 4)
  - [ ] Unit tests for validators (good/bad cases; HTTPS posture; normalization/dedup).
  - [ ] Integration tests validating computed settings in `src/backend/core/tests/test_settings.py`.
  - [ ] Update `docs/env.md` + `docs/resource_server.md`/other relevant pages with the split model and examples.

## Dev Notes

- **Key unknown to resolve early:** where exactly `lasuite.oidc_login` validates redirects (host-only vs full-URI). This determines whether you can enforce path-level allowlisting without patching third-party libraries.
- **Derivation principle:** treat `DRIVE_PUBLIC_URL` as the canonical source of truth; derived values are always present, operator additions are additive, never replace canonical entries.
- **No-wildcards rule:** keep allowlists concrete and deterministic to avoid “works in dev / insecure in prod” drift.
- **Rollout:** start by computing derived lists and logging/raising only on clearly invalid entries; avoid breaking existing deployments that rely on current `OIDC_*` behavior without a migration note.

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale)

### References

- [Source: `src/backend/drive/settings.py` — OIDC settings (`OIDC_REDIRECT_*`) and `Base.post_setup`]
- [Source: `src/backend/core/api/viewsets.py` — `SDK_CORS_ALLOWED_ORIGINS` consumption]
- [Source: `src/backend/core/urls.py` — OIDC routes included under API prefix]
- [Source: `docs/env.md` — CORS/CSRF/OIDC/Find env vars]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

### Completion Notes List

### File List
