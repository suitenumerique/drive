# Run report — Story 5.2 (No-leak error contract)

Run key: 5.2

## Summary

- Removed raw S3 object keys/filenames from backend and security logs by hashing.
- Sanitized malware detection callback logging and stored `error_info` (allow-list).
- Added an S3 gateway compatibility fallback for metadata updates when `CopyObject`
  is rejected (SeaweedFS baseline), keeping logs no-leak.
- Updated tests to assert no-leak logging and to use configured S3 region.

## Files changed

See `files-changed.txt`.

## Verification (dev-owned)

Executed (UTC): 2026-02-11T14:50:51Z

- `backend.lint` (`make lint`): PASS
- `backend.tests` (`make test-back`): PASS

See `run-report.md` / `run-report.json` for gate details.

## Evidence / outputs

- Gate runner report: `run-report.md`
- Gate results (machine-readable): `gates/gate-results.json`

