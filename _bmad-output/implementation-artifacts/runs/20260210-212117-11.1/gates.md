# Gates — Story 11.1

- `CT-S3` (SeaweedFS profile): FAIL (CT-S3-007 Copy+MetadataDirective=REPLACE)
  - Evidence: `_bmad-output/implementation-artifacts/ct-s3/latest.txt` →
    `.../report.md`
- `make lint`: PASS
- Backend tests: PASS (pytest in compose, MinIO-like test env)

Non-blocking checks (do not wait in this fork):

- Docker Hub build-and-push (backend/frontend)
- Crowdin sync
- Frontend e2e matrix (chromium/firefox/webkit)
