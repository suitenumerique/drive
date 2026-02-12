# Story 9.5 — SMB preview support (capability-driven, deterministic)

## Summary

- Backend: capability-gated mount preview endpoint streams SMB file content and
  returns a deterministic "preview not available" error for non-previewable
  files.
- UI: mounts explorer adds an explicit preview page that distinguishes
  "preview not available" from "access denied" with a next action.

## Verification

- Gates runner: see `run-report.md`
- Expected result: PASS
- Notes:
  - `backend.lint`: PASS
  - `backend.tests`: PASS (includes new mount preview tests)
  - `frontend.lint`: PASS
  - `docs.consistency`: PASS
  - `no_leak.scan_bmad_output`: PASS

## No-leak

- No credentials, signed URLs, or raw SMB paths are logged or written to artifacts.

