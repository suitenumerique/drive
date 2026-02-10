# CT-S3 (S3 Contract Tests)

CT-S3 is a Drive-integrated contract test suite for S3-compatible object storage.
It is **audience-aware** and reports results deterministically with **no-leak**
evidence only.

## Audiences

- `INTERNAL_PROXY`: requests made by the backend / edge proxy towards S3.
- `EXTERNAL_BROWSER`: presigned URLs that a browser uses for uploads.

## Docker-first: how to run

Run CT-S3 via the repository entrypoint:

- `./bin/ct_s3`

Common options:

- `./bin/ct_s3 --profile seaweedfs-s3`
- `./bin/ct_s3 --strict-range-206`

## Artifacts (deterministic)

Each run writes:

- `_bmad-output/implementation-artifacts/ct-s3/<run_id>-<profile>/report.md`
- `_bmad-output/implementation-artifacts/ct-s3/<run_id>-<profile>/report.json`
- `_bmad-output/implementation-artifacts/ct-s3/latest.txt` (relative pointer)

The JSON report is designed for automation:

- stable keys + stable ordering
- per-check `failure_class` + `next_action_hint`
- safe evidence only (hashes + status codes + request ids)

## No-leak

CT-S3 artifacts must never contain:

- credentials, tokens, or SigV4 headers,
- signed URLs or query signatures,
- raw object keys or internal URLs.

### Safe evidence allow-list

CT-S3 reports include `evidence` objects that are **allow-listed** at creation
time. Allowed values are limited to:

- status codes and request ids,
- truncated hashes (for hosts/keys), and
- small booleans/integers needed for determinism.

If a CT-S3 check attempts to emit a non-allow-listed evidence field, the runner
fails fast rather than risk leaking sensitive data.
