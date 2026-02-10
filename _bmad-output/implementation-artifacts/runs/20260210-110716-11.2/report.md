# Run Report — Story 11.2 (SeaweedFS S3 auth + signed PUT proof)

- Run ID: `20260210-110716-11.2`
- Date (UTC): 2026-02-10
- Repo: `/root/Apoze/drive`

## Goal

Fix SeaweedFS S3 gateway auth so the dev key `drive` is accepted, and prove the Docker baseline supports **signed PUT** + **bucket versioning enable**.

## Root cause

SeaweedFS S3 gateway was running without server-side credentials configured, and IAM rejected requests signed with access key `drive` (observed as "attempted key 'drive' not found").

## Fix (minimal)

- Configure SeaweedFS S3 gateway server credentials via env vars:
  - `AWS_ACCESS_KEY_ID=drive`
  - `AWS_SECRET_ACCESS_KEY=password`
- Implemented via `env.d/development/seaweedfs-s3` and `env_file:` on `seaweedfs-s3` in `compose.yaml`.

## Smoke / proof

Executed commands are in `commands.log` (secret redacted).

Results:

- Signed PUT (mc) **PASS**:
  - `mc cp /tmp/hello.txt drive/drive-media-storage/hello.txt` succeeded
  - `mc stat` returned a `VersionID` for `hello.txt`
- Versioning enable **PASS**:
  - `mc version enable drive/drive-media-storage` succeeded (not "Access Denied")

## Notes

- This run supersedes the earlier 20260210-102015-11.2 report: that run did not prove signed PUT and could fail due to missing S3 gateway server credentials.
