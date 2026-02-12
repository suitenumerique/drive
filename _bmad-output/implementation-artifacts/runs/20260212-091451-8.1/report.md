# Story 8.1 — Run report (20260212-091451-8.1)

## Summary

- Adds deterministic refs-only secret validation for mounts configuration.
- Enforces that mount secret material is never provided directly in configuration
  by validating `MOUNTS_REGISTRY`/`MOUNTS_REGISTRY_FILE` in `config_preflight`.
- Keeps errors no-leak (never echo secret values or sensitive file paths).

## Verification

- backend.lint: PASS (make lint)
- backend.tests: PASS (make test-back)

## Artifacts

- commands: _bmad-output/implementation-artifacts/runs/20260212-091451-8.1/commands.log
- gates: _bmad-output/implementation-artifacts/runs/20260212-091451-8.1/gates.md
- files changed: _bmad-output/implementation-artifacts/runs/20260212-091451-8.1/files-changed.txt
