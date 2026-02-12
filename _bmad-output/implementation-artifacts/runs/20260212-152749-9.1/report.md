# Story 9.1 — SMB mount configuration schema + deterministic validation

## Summary

Added deterministic validation and normalization for SMB mount configuration,
including refs-only secret references for passwords.

## What changed

- Enforced SMB mount params schema (`provider: smb`):
  - required: `server`, `share`, `username`
  - `port` defaults to 445 and is validated when provided
  - optional: `domain`/`workgroup`, `base_path`, timeout fields
- Enforced refs-only password configuration:
  - reject direct `password` values
  - accept refs-only `password_secret_ref` and/or `password_secret_path`
- Updated documentation and unit tests accordingly.

## Verification

- Gates runner: see `run-report.md` (PASS) and `gates.md`.
