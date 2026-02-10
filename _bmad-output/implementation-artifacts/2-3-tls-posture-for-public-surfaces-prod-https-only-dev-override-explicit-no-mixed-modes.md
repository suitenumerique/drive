# Story 2.3: TLS posture for public surfaces (prod HTTPS-only, dev override explicit, no mixed modes)

Status: done

## Story

As an operator,
I want TLS rules that enforce HTTPS on all public surfaces in production, with an explicit dev-only override (centralized),
So that `DRIVE_PUBLIC_URL`-derived URLs are safe and consistent across redirects, share links, and WOPI.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] Define the “public surfaces” set to enforce (AC: 1)
  - [ ] `DRIVE_PUBLIC_URL` itself
  - [ ] OIDC redirects/origins derived from it
  - [ ] share-link URLs
  - [ ] WOPI allowlists/launch URLs
- [ ] Implement centralized TLS posture logic (AC: 1–4)
  - [ ] Production posture: HTTPS-only for public surfaces, no mixed modes.
  - [ ] Dev posture: allow HTTP only when explicit override is enabled.
  - [ ] Normalize URL forms deterministically (slashes/trailing slash).
- [ ] Wire into config preflight/validation (AC: 1–4)
  - [ ] Emit stable `failure_class` + `next_action_hint` on violations.
  - [ ] Keep outputs no-leak (do not echo secrets).
- [ ] Update docs (AC: 1–4)
  - [ ] Document the override and its dev-only intent.
  - [ ] Ensure operator guidance is explicit and deterministic.
- [ ] Verification (AC: 1–4)
  - [ ] Tests covering prod vs dev override behavior and normalization.

## Dev Notes

- This story is intentionally coupled to Story 1.1 (`DRIVE_PUBLIC_URL`) and should reuse the same normalization/validation helpers.
- Prefer enforcing via deterministic validation/preflight rather than runtime surprises.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.3 Acceptance Criteria]
- [Source: `_bmad-output/implementation-artifacts/1-1-canonical-drive-public-url-validation-and-deterministic-derivations.md` — override and normalization intent]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260210-141727-2.3/report.md`

### Completion Notes List

- Centralized TLS posture for public surfaces:
  - HTTPS-only in production posture (rejects `http://` even if `DRIVE_ALLOW_INSECURE_HTTP=true`).
  - DEV-only HTTP override: `http://` accepted only when `DEBUG=true` and `DRIVE_ALLOW_INSECURE_HTTP=true`.
- Enforced “no mixed TLS modes” for validated public surfaces (DRIVE_PUBLIC_URL, WOPI_SRC_BASE_URL, URL-form OIDC redirect entries) under HTTPS-only posture.
- Added `join_public_url()` helper to build derived public URLs without double slashes.
- Updated operator docs to make the dev-only override and HTTPS-only production posture explicit.

### File List

- `src/backend/core/utils/public_url.py`
- `src/backend/drive/settings.py`
- `src/backend/core/tests/test_public_url.py`
- `src/backend/core/tests/test_settings.py`
- `env.d/development/common`
- `docs/env.md`
- `_bmad-output/implementation-artifacts/runs/20260210-141727-2.3/report.md`
