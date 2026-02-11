# Run report — Story 5.3 (Deterministic upload recovery patterns)

Story file: `_bmad-output/implementation-artifacts/5-3-deterministic-recovery-patterns-for-uploads-and-media-edge-failures-cleanup-actionable-next-steps.md`

## Scope

- In: pending upload TTL (deterministic `expired`), idempotent retry via policy refresh,
  actionable no-leak UI states for upload failures, and operator-facing no-leak logs
  for `/media-auth` not-ready items.
- Out: Share links and MountProvider stories.

## Changes

- Backend:
  - Add `upload_started_at` and `ITEM_UPLOAD_PENDING_TTL_SECONDS` to time-bound
    `PENDING` uploads and surface `EXPIRED` deterministically.
  - Add `POST /api/v1.0/items/<id>/upload-policy/` to re-initiate a pending upload
    on the same item (avoids duplicate "ghost" items).
  - Deny `upload-ended` for expired sessions with actionable, no-leak messaging and
    `failure_class` + `next_action_hint` in logs.
- Frontend:
  - Improve upload toast to keep failed files visible and allow retry/re-initiate.
  - Add explicit messaging for not-ready / expired items when attempting download.

## Verification

Executed (UTC): 2026-02-11T18:18:06Z

- `backend.lint` (`make lint`): PASS
- `backend.tests` (`make test-back`): PASS
- `frontend.lint` (`make frontend-lint`): PASS

See `run-report.md` / `run-report.json` and `gates/gate-results.json` for details.

## Artifacts

- Run folder: `_bmad-output/implementation-artifacts/runs/20260211-181806-5.3/`
- Changed files list: `files-changed.txt`
- Commands log: `commands.log`

## Follow-ups

- [ ] Consider surfacing `upload_policy` in the frontend `abilities` type if/when
      UI gating needs it explicitly.

