# Story 2.2: Nginx reference edge configuration (dev/prod aligned) for `/media` auth_request + SigV4 propagation

Status: ready-for-dev

## Story

As an operator,
I want an Nginx reference configuration (dev and prod aligned) that implements the proxy-agnostic `/media` edge contract,
So that I can deploy Drive behind Nginx (or replicate the same behavior in another proxy) while preserving the media auth flow and SigV4 requirements.

## Acceptance Criteria

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

## Tasks / Subtasks

- [ ] Inventory current Nginx dev/prod configs and `/media` routing (AC: 1, 3)
  - [ ] Locate the dev Nginx config and confirm how `/media` is currently served.
  - [ ] Locate the prod Nginx config and compare it with dev behavior (auth subrequest, headers, path rewriting).
- [ ] Implement/align the auth subrequest pattern for `/media` (AC: 1, 3)
  - [ ] Ensure `/media` uses `auth_request` to the backend media-auth endpoint.
  - [ ] Ensure auth responses map correctly to S3 proxying behavior (401/403 handling, caching semantics if any).
- [ ] Forward SigV4 headers from media-auth to S3 (AC: 2)
  - [ ] Forward all required headers including optional STS token header when present.
  - [ ] Ensure Nginx does not overwrite or normalize critical SigV4 headers.
- [ ] Add “no-leak” logging defaults/guidance (AC: 4)
  - [ ] Ensure access/error logs do not include SigV4 secrets by default.
  - [ ] If logs are configurable, document the safe configuration explicitly.
- [ ] Update docs / edge contract notes (AC: 5)
  - [ ] Keep proxy-agnostic contract wording; present Nginx as reference implementation.
- [ ] Verification (AC: 1–5)
  - [ ] Docker-first smoke: `/media` works for preview/download via Nginx and failures are actionable/no-leak.
  - [ ] Confirm headers are forwarded correctly (including `X-Amz-Security-Token` when applicable).

## Dev Notes

- Nginx reference configs are expected under `docker/files/**/etc/nginx/conf.d/`.
- Backend contract endpoint referenced in planning artifacts: `/api/v1.0/items/media-auth/`.
- No-leak requirement: ensure Nginx logs do not capture SigV4 headers (especially `Authorization` and `X-Amz-Security-Token`).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.2 Acceptance Criteria]
- [Source: `_bmad-output/project-context.md` — `/media` edge contract and SigV4 header list]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

