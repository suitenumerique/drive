# Run report — Story 2.5 (PR #23)

- Story: `2.5` — `_bmad-output/implementation-artifacts/2-5-docker-first-upgrade-rollback-runbook-deterministic-post-action-smoke-checklist.md`
- Branch: `story/2.5-upgrade-rollback-runbook`

## Scope

In scope:

- Docker-first upgrade runbook (compose baseline).
- Docker-first rollback runbook (compose baseline, with explicit DB restore note).
- Deterministic post-action smoke checklist (operator-run), expanded to include:
  login, browse, preview, upload, `/media` flow (edge contract reference), and
  optional public share checks.

Out of scope:

- Any Kubernetes/Helm deployment procedures.
- Implementing mount-backed public share semantics (only documented checks).

## Implementation summary

- Added `docs/selfhost/upgrade.md` with explicit ordering (pin/pull or build →
  quiesce → migrate → restart → smoke).
- Added `docs/selfhost/rollback.md` with explicit DB restore requirement note
  when migrations may be non-backward-compatible.
- Expanded `docs/selfhost/smoke-checklist.md` into deterministic PASS/FAIL steps
  matching the story’s post-action checklist requirements.
- Updated entry points to the new runbooks from `docs/selfhost/README.md` and
  `docs/installation/README.md`.
- Updated `CHANGELOG.md` (Unreleased) for the docs additions.

## Verification

See `commands.log` for the exact commands and outputs.

Manual checks (doc quality):

- Steps are concrete and Docker-first (no Kubernetes assumptions): PASS
- Examples contain no secrets / signed URLs / SigV4 headers: PASS

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-084234-2.5/`
- Gates summary: `_bmad-output/implementation-artifacts/runs/20260211-084234-2.5/gates.md`

