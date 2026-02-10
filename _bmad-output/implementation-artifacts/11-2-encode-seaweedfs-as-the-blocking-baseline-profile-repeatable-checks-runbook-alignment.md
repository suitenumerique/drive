# Story 11.2: Encode SeaweedFS as the blocking baseline profile (repeatable checks + runbook alignment)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer/operator,
I want SeaweedFS S3 gateway behavior encoded as the blocking CT-S3 baseline profile with repeatable checks, and to make SeaweedFS the default self-host/dev/CI baseline (not MinIO),
So that “works on SeaweedFS” is a deterministic, enforceable v1 promise and the Sprint 0 baseline matches what gates/runbooks claim.

**Acceptance Criteria:**

**Given** the SeaweedFS profile is selected
**When** CT-S3 runs
**Then** the baseline expectations are explicit, repeatable, and produce stable `failure_class` + `next_action_hint` on failure.

**Given** self-host docs/runbooks reference the S3 baseline
**When** an operator follows them for Docker/compose deployments
**Then** they use SeaweedFS as the default baseline and clearly state MinIO is (at most) an explicitly non-blocking fixture.

**Given** Sprint 0 baseline is used (dev/CI)
**When** a developer runs the default Docker/compose path
**Then** the default S3 path is SeaweedFS (not MinIO), without requiring undocumented “extra steps”.

**Given** MinIO remains available as a fixture
**When** it is used
**Then** it is clearly labeled non-blocking and is not used for blocking gates, baseline guarantees, or operator smoke check assertions.

## Acceptance Criteria (numbered)

1. **Given** the SeaweedFS profile is selected **When** CT-S3 runs **Then** the baseline expectations are explicit, repeatable, and produce stable `failure_class` + `next_action_hint` on failure.
2. **Given** self-host docs/runbooks reference the S3 baseline **When** an operator follows them for Docker/compose deployments **Then** they use SeaweedFS as the default baseline and clearly state MinIO is (at most) an explicitly non-blocking fixture.
3. **Given** Sprint 0 baseline is used (dev/CI) **When** a developer runs the default Docker/compose path **Then** the default S3 path is SeaweedFS (not MinIO), without requiring undocumented “extra steps”.
4. **Given** MinIO remains available as a fixture **When** it is used **Then** it is clearly labeled non-blocking and is not used for blocking gates, baseline guarantees, or operator smoke check assertions.

## Tasks / Subtasks

- [ ] Define the “SeaweedFS baseline” profile inputs (AC: #1, #3)
  - [ ] Identify the exact env vars/config keys that select the S3 provider profile in Drive today (or introduce the minimal selector if missing).
  - [ ] Document the canonical SeaweedFS baseline profile values (endpoints, signature expectations, audience mapping) in a single place used by CT-S3 + docs.

- [ ] Align Docker/compose default baseline to SeaweedFS (AC: #2, #3)
  - [ ] Update `compose.yaml` (and any referenced env files) so the default `docker compose up` path uses SeaweedFS S3 gateway for S3 storage.
  - [ ] Keep MinIO as an optional fixture only (do not delete it), but ensure it is not the default and is clearly labeled “non-blocking”.
  - [ ] Ensure the default path stays Docker-first; do not add K8s/Helm requirements.

- [ ] Align documentation and runbooks (AC: #2, #4)
  - [ ] Update self-host docs/runbooks to reflect SeaweedFS as baseline and MinIO as optional/non-blocking.
  - [ ] Add an explicit “baseline promise” note: blocking guarantees/gates are for SeaweedFS.
  - [ ] Ensure language is deterministic: “default uses SeaweedFS”, not “recommended”.

- [ ] Align gates/CI selection to the baseline (AC: #1, #3, #4)
  - [ ] Ensure the blocking CT-S3 gate targets SeaweedFS (`s3.contracts.seaweedfs` or equivalent).
  - [ ] Ensure CI uses SeaweedFS for the default storage profile when running blocking gates.
  - [ ] If MinIO is exercised, ensure it is explicitly non-blocking (separate optional gate).

## Dev Notes

- Constraints (v1):
  - SeaweedFS is the Sprint 0 baseline; MinIO may remain only as an explicitly non-blocking fixture.
  - Docker-first v1; Kubernetes remains reference-only (as-is), no K8s improvements or K8s gates.
  - No-leak: do not log/emit credentials, signed headers, internal endpoints in artifacts.

- Implementation decision (Docker/compose baseline):
  - The baseline `seaweedfs-s3` service **must** accept SigV4-signed requests from Drive/boto3 and `mc`.
  - For Sprint 0, do this via **explicit env vars on the `seaweedfs-s3` container**:
    - `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (SeaweedFS S3 server fallback admin credentials)
  - Keep the Drive app/client credentials in `env.d/development/common` as:
    - `AWS_S3_ACCESS_KEY_ID` + `AWS_S3_SECRET_ACCESS_KEY`
  - Use the same values for both sets in dev (e.g. `drive` / `password`) to keep the baseline repeatable.
  - Do **not** add a `config.json` IAM file for this story (keep the change minimal and Docker-first); advanced IAM config may be introduced later if needed.

### References

- `_bmad-output/planning-artifacts/epics.md` (Additional Requirements: SeaweedFS baseline + Sprint 0; Epic 11 Story 11.2 AC)
- `_bmad-output/planning-artifacts/development-order.md` (Sprint 0 placement)

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260210-102015-11.2/report.md`
- `_bmad-output/implementation-artifacts/runs/20260210-110716-11.2/report.md`

### Completion Notes List

- Docker Compose baseline S3 provider switched to SeaweedFS S3 gateway (`seaweedfs-s3`), published on `localhost:9000`.
- MinIO kept as an explicit non-baseline fixture via `minio-fixture` compose profile (no longer the default).
- SeaweedFS S3 gateway server auth configured via `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (dev: `drive`/`password`) to avoid IAM rejecting signed requests.
- Signed PUT proof executed via `mc cp` to `drive/drive-media-storage/hello.txt` and `mc stat` returned a `VersionID`.
- Bucket versioning enable confirmed via `mc version enable drive/drive-media-storage` (not Access Denied).
- Nginx `/media` proxy defaults to SeaweedFS gateway; DS Proxy remains an optional profile.
- Docs updated to state “baseline = SeaweedFS” and “MinIO = optional fixture”.

### File List

- `compose.yaml`
- `env.d/development/common`
- `docker/files/development/etc/nginx/conf.d/default.conf`
- `docker/files/production/etc/nginx/conf.d/default.conf`
- `docs/ds_proxy.md`
- `docs/installation/kubernetes.md`
- `README.md`
- `_bmad-output/implementation-artifacts/runs/20260210-102015-11.2/report.md`
