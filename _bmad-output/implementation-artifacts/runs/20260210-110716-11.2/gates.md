# Gates (manual, Story 11.2)

## docker.compose.seaweedfs-baseline-smoke (PASS)

- `docker compose -f compose.yaml up -d seaweedfs-s3 createbuckets`
- Signed PUT proof (mc): `mc cp` to `drive/drive-media-storage/hello.txt` succeeded and `mc stat` returned a `VersionID`
- `mc version enable drive/drive-media-storage` succeeded (not "Access Denied")

## Notes

- Root cause of previous failure: SeaweedFS S3 gateway did not have server-side credentials configured, causing IAM to reject access key `drive` ("attempted key 'drive' not found").
- Fix: provide `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` to `seaweedfs-s3` via `env.d/development/seaweedfs-s3`.
