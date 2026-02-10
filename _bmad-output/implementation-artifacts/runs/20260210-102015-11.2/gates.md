# Gates (manual, Story 11.2)

## docker.compose.seaweedfs-baseline-smoke (PASS)

- Started baseline storage services: `seaweedfs-*` + `createbuckets`
- Confirmed S3 gateway reachable on host `http://127.0.0.1:9000` (HTTP 403 without auth is expected)
- Confirmed bucket `drive-media-storage` exists and versioning enable command succeeded in this run

## drive-gates-runner (SKIPPED)

- Expected script `bin/agent-check.sh` is not present in this workspace, so deterministic gates runner could not be executed.

