# Failure reporting schema (deterministic, no-leak)

This document standardizes how automated checks (gates) and operator-facing
artifacts report failures.

## Required fields

Every reported failure MUST include:

- `failure_class`: a stable code identifier (string)
- `next_action_hint`: a short actionable hint (string)

Successful checks SHOULD include these fields as explicit `null` to preserve a
stable schema (`failure_class=null`, `next_action_hint=null`).

## `failure_class` format

- Exactly **3 segments**: `domain.category.reason`
- Segments are separated by `.`
- Each segment is `snake_case`

Examples:

- `s3.signature.host_mismatch_internal`
- `no_leak.scan.match_found`
- `gate.backend.lint_failed`

Do not encode sensitive detail in the code itself (no hostnames, paths, keys,
tokens, URLs).

## `audience` (where applicable)

When a check’s meaning depends on who is making the request, include:

- `audience`: one of `INTERNAL_PROXY` or `EXTERNAL_BROWSER`

Example: CT-S3 includes `audience` for every result item.

## Safe evidence (allow-listed only)

If you include evidence:

- evidence MUST be allow-listed “by construction”
- evidence MUST be no-leak (no secrets, credentials, signed URLs, SigV4 headers,
  raw object keys, or internal URLs)
- prefer hashes, status codes, and request ids

