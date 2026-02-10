# Run Report — Story 11.3 (CT-S3 safe evidence allow-listing)

- Run ID: `20260210-212117-11.3`
- Date (UTC): 2026-02-10
- Branch: `story/11.3-ct-s3-evidence-allowlist` (stacked on `story/11.1-ct-s3-runner`)
- PR: #18 (draft)

## Goal

Make CT-S3 evidence **no-leak by construction** by enforcing an allow-listed
schema at evidence creation time, with regression tests.

## What changed

- Added an explicit CT-S3 evidence allow-list (`core.ct_s3.evidence`).
- Enforced allow-listed evidence shaping in `CheckResult` and for the CT-S3
  profile summary (fails fast on unexpected evidence fields).
- Added regression tests proving unknown/invalid evidence shapes are rejected
  without echoing sensitive values.
- Documented the safe evidence rules in `docs/ct-s3.md`.

## Verification (dev-owned)

The developer (human) must run and record results (agent does not run lint/tests):

- `make lint`
- `make test-back`

Record outcomes in `gates.md` after running.

