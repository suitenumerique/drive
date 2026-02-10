# Run Report — Story 11.1 (CT-S3 runner)

- Run ID: `20260210-212117-11.1`
- Date (UTC): 2026-02-10
- Branch: `story/11.1-ct-s3-runner`
- PR: #11 (draft)

## Goal

Deliver a Drive-integrated CT-S3 runner that:

- models explicit audiences (`INTERNAL_PROXY` / `EXTERNAL_BROWSER`)
- validates connect_url vs signed_host invariants
- writes deterministic artifacts (human + JSON) under `_bmad-output/implementation-artifacts/`
- stays **no-leak** (no secrets, no signed URLs, no SigV4 headers, no raw keys)

## What changed

- Added `ct_s3` Django management command and `./bin/ct_s3` Docker-first entrypoint.
- Implemented the baseline CT-S3 checks (SeaweedFS profile) with deterministic
  `failure_class` + `next_action_hint` and safe evidence (hashes only).
- Wrote deterministic CT-S3 artifacts under `_bmad-output/implementation-artifacts/ct-s3/`
  with a `latest.txt` pointer.
- Documented how to run CT-S3 in `docs/ct-s3.md`.

## Verification (dev-owned)

The developer (human) must run and record results (agent does not run lint/tests/smokes):

- `./bin/ct_s3 --profile seaweedfs-s3`
- Optional strictness: `./bin/ct_s3 --strict-range-206`
- Recommended repo gates:
  - `make lint`
  - `make test-back`

Record outcomes in `gates.md` after running.

## Artifacts

- CT-S3 run outputs: `_bmad-output/implementation-artifacts/ct-s3/` (per-run folder)
- This run folder: `_bmad-output/implementation-artifacts/runs/20260210-212117-11.1/`

## Risks / follow-ups

- Confirm CT-S3 behavior in at least one intentional failure scenario and ensure
  artifacts remain no-leak in that case.

