# Story 1.1: Canonical `DRIVE_PUBLIC_URL` validation and deterministic derivations

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to configure a canonical public base URL (`DRIVE_PUBLIC_URL`) with strict validation and deterministic derivations,
So that all public-facing URLs/origins are consistent and misconfiguration fails early with actionable, no-leak errors.

**Acceptance Criteria:**

**Given** `DRIVE_PUBLIC_URL` is configured as an absolute URL with a scheme and host (and no query/fragment; path is empty or `/`)
**When** configuration preflight/validation runs
**Then** the system accepts it and uses a normalized base value for all derivations (e.g., no duplicate slashes).

**Given** `DRIVE_PUBLIC_URL` has a trailing slash (e.g., `https://drive.example.com/`)
**When** configuration preflight/validation runs
**Then** the system normalizes it (e.g., removes the trailing slash) so derived public URLs remain consistent.

**Given** `DRIVE_PUBLIC_URL` is invalid (missing host, includes query/fragment, includes an unexpected path, or otherwise not a valid canonical public base URL)
**When** configuration preflight/validation runs
**Then** the system fails early with a deterministic `failure_class` and a `next_action_hint`, without leaking secrets or sensitive paths.

**Given** `DRIVE_PUBLIC_URL` uses `http://` and the insecure dev override is not enabled
**When** configuration preflight/validation runs in a production deployment
**Then** the system rejects the configuration with a deterministic `failure_class` and a `next_action_hint` guiding to set `https://` or enable the dev-only override explicitly (e.g., `DRIVE_ALLOW_INSECURE_HTTP=true`).

## Acceptance Criteria

1. **Given** `DRIVE_PUBLIC_URL` is configured as an absolute URL with a scheme and host (and no query/fragment; path is empty or `/`) **When** configuration preflight/validation runs **Then** the system accepts it and uses a normalized base value for all derivations (e.g., no duplicate slashes).
2. **Given** `DRIVE_PUBLIC_URL` has a trailing slash (e.g., `https://drive.example.com/`) **When** configuration preflight/validation runs **Then** the system normalizes it (e.g., removes the trailing slash) so derived public URLs remain consistent.
3. **Given** `DRIVE_PUBLIC_URL` is invalid (missing host, includes query/fragment, includes an unexpected path, or otherwise not a valid canonical public base URL) **When** configuration preflight/validation runs **Then** the system fails early with a deterministic `failure_class` and a `next_action_hint`, without leaking secrets or sensitive paths.
4. **Given** `DRIVE_PUBLIC_URL` uses `http://` and the insecure dev override is not enabled **When** configuration preflight/validation runs in a production deployment **Then** the system rejects the configuration with a deterministic `failure_class` and a `next_action_hint` guiding to set `https://` or enable the dev-only override explicitly (e.g., `DRIVE_ALLOW_INSECURE_HTTP=true`).
## Tasks / Subtasks

- [ ] Add settings inputs for a canonical public base URL (AC: 1, 2, 4)
  - [ ] Introduce `DRIVE_PUBLIC_URL` (string/URL) and `DRIVE_ALLOW_INSECURE_HTTP` (bool; dev-only override).
  - [ ] Decide enforcement mode: treat `DEBUG=False` (and/or `Production`-derived environments) as “production posture”.
  - [ ] Document env vars in `docs/env.md` (include examples and default behavior when unset).
- [ ] Implement deterministic normalization + validation helper (AC: 1, 2, 3, 4)
  - [ ] Add a small helper module (e.g. `src/backend/core/utils/public_url.py`) that:
    - parses absolute URLs safely,
    - rejects query/fragment/userinfo,
    - restricts path to empty or `/`,
    - normalizes (e.g., trims trailing slash; lowercases scheme/host where safe),
    - enforces HTTPS in production posture unless `DRIVE_ALLOW_INSECURE_HTTP=true`,
    - raises a structured error carrying `failure_class` + `next_action_hint`.
  - [ ] Define stable `failure_class` values (e.g. `config.public_url.*`) and add them to `docs/failure-class-glossary.md`.
- [ ] Wire validation into settings boot (AC: 1, 2, 3, 4)
  - [ ] In `src/backend/drive/settings.py:Base.post_setup`, if `DRIVE_PUBLIC_URL` is set:
    - normalize it once and store the normalized value back onto the class,
    - fail fast with a deterministic `ValueError` message that includes `failure_class` + `next_action_hint` (no-leak).
  - [ ] Keep behavior no-op when `DRIVE_PUBLIC_URL` is unset (no surprise breakage during rollout).
- [ ] Add targeted tests (AC: 1, 2, 3, 4)
  - [ ] Unit tests for the helper (normalization + failure classes).
  - [ ] Integration-style tests around `Base.post_setup` in `src/backend/core/tests/test_settings.py` (invalid → raises; trailing slash → normalized).
  - [ ] Add a regression test that error strings do not echo secrets/query params (no-leak guardrail).

## Dev Notes

- **Where to validate:** the repo already uses `src/backend/drive/settings.py:Base.post_setup` for cross-setting validation (e.g., OIDC email duplication guard). This story should follow the same pattern.
- **No-leak constraint:** error messages should be actionable but avoid echoing full URLs if they may contain sensitive details; prefer `failure_class` + `next_action_hint` and redact/omit input values.
- **Production posture:** `Development.DEBUG=True` vs `Production.SECURE_SSL_REDIRECT=True` suggests using `DEBUG` (or environment class) as the switch for HTTPS enforcement.
- **Scope:** keep v1 limited to canonical base URL normalization/validation; downstream derivations should be introduced story-by-story to avoid breaking existing config.

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
- Detected conflicts or variances (with rationale)

### References

- [Source: `src/backend/drive/settings.py` — `Base.post_setup` validation pattern]
- [Source: `src/backend/drive/settings.py` — environment classes `Development`/`Production`]
- [Source: `docs/env.md` — environment variable documentation table]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260210-125506-1.1/report.md`

### Completion Notes List

- Added `DRIVE_PUBLIC_URL` + `DRIVE_ALLOW_INSECURE_HTTP` settings inputs in `drive.settings.Base`.
- Implemented deterministic validation/normalization helper in `core.utils.public_url` (no query/fragment/userinfo; path empty or `/`; trailing slash removed; HTTPS enforced in production posture unless overridden).
- Wired validation into `Base.post_setup` (fail-fast, no-leak error message containing stable `failure_class` + `next_action_hint`).
- Added targeted tests covering AC 1–4, including a no-leak regression test.
- Updated operator docs (`docs/env.md`) and failure class glossary.

### File List

- `src/backend/core/utils/public_url.py`
- `src/backend/drive/settings.py`
- `src/backend/core/tests/test_public_url.py`
- `src/backend/core/tests/test_settings.py`
- `docs/env.md`
- `docs/failure-class-glossary.md`
- `_bmad-output/implementation-artifacts/runs/20260210-125506-1.1/report.md`
