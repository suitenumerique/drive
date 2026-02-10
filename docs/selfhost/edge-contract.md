# Edge contract (v1) — `/media` behind a reverse proxy

This document specifies the **proxy-agnostic** v1 edge contract for Drive’s `/media`
paths when deployed behind **any reverse proxy**.

Nginx configurations in this repository are **reference implementations only**. Your
proxy may be Nginx, Traefik, Caddy, HAProxy, an ingress controller, etc.

## Audience model (required)

Drive’s media paths are validated and debugged using two audiences:

- **INTERNAL_PROXY**: your reverse proxy talking to the S3-compatible upstream.
- **EXTERNAL_BROWSER**: end-user browser uploading directly to the S3-compatible
  endpoint via a signed URL (presigned PUT).

These audiences have different constraints (notably on the **signed host**).

## Required routes

Your reverse proxy must provide:

- `GET /media/<key>` — download item media
- `GET /media/preview/<key>` — download preview media (when applicable)
- An **auth subrequest endpoint** used by the proxy:
  - `GET /media-auth` (edge path), which proxies to:
    - `GET /api/v1.0/items/media-auth/` (backend endpoint)

The backend endpoint authorizes the request and returns **SigV4 headers** that the
proxy must forward to the S3 upstream.

## Auth subrequest contract

The proxy must:

- Forward the user’s session (cookies) to the backend subrequest.
- Provide the original request URL to the backend via `X-Original-URL`.
  - The backend matches `X-Original-URL` against the expected `/media/...` pattern.
- Disable request body forwarding for the subrequest (`GET` only).

## SigV4 header propagation (required)

When the auth subrequest succeeds, the backend responds with headers that the proxy
must copy into the **upstream S3 request**:

- `Authorization`
- `X-Amz-Date`
- `X-Amz-Content-SHA256`
- `X-Amz-Security-Token` (optional; required when using temporary credentials)

If any required header is missing, the S3 upstream can return
`403 SignatureDoesNotMatch` or similar authorization failures.

## Signed host invariants (required)

SigV4 signatures bind the request to a specific host.

- For **INTERNAL_PROXY**, the upstream request **Host** header must match the host
  implied by `AWS_S3_ENDPOINT_URL` (the backend’s S3 endpoint used for signing).
- For **EXTERNAL_BROWSER** (presigned PUT), the browser must use a host that matches
  the signing endpoint:
  - If `AWS_S3_DOMAIN_REPLACE` is set, it becomes the browser-facing signing base URL.
  - Otherwise, the browser-facing signing base URL is `AWS_S3_ENDPOINT_URL`.

Do not rewrite the upstream host in a way that causes a mismatch with the signature.

## No-leak logging guidance (required)

Do not log SigV4 headers or full request URLs containing signatures:

- `Authorization`
- `X-Amz-Date`
- `X-Amz-Content-SHA256`
- `X-Amz-Security-Token`

If you need diagnostics, prefer safe evidence (status codes, request IDs, and
sanitized hostnames).

