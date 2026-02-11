# Run report — Story 12.2 (PR #25)

- Story: `12.2` — `_bmad-output/implementation-artifacts/12-2-standardize-failure-class-next-action-hint-across-gates-and-operator-facing-artifacts.md`
- Branch: `story/12.2-failure-taxonomy`

## Scope

In scope:

- Document a stable, no-leak failure reporting schema (`failure_class`,
  `next_action_hint`, optional `audience`, safe evidence).
- Expand the failure class taxonomy to include gates runner / no-leak scanning /
  mirror + unimplemented cases.
- Add a targeted backend test that locks CT-S3 result schema fields
  (`failure_class`, `next_action_hint`).

Out of scope:

- Implementing additional gates or CI wiring (Story 12.4).

## Implementation summary

- Added `docs/failure-reporting-schema.md` (stable fields + no-leak rules).
- Updated `docs/failure-class-glossary.md` with additional failure classes for
  gates runner / no-leak scanning / mirror.
- Added backend tests ensuring CT-S3 `CheckResult` serialization always includes
  `failure_class` + `next_action_hint` fields.
- Fixed `bin/pylint` to deterministically skip when no backend Python files are
  modified (avoids false failures during `make lint`).

## Verification

- `make lint`: PASS
- `bin/pytest src/backend/core/tests/test_ct_s3_failure_schema.py`: PASS

## Artifacts

- Story run folder: `_bmad-output/implementation-artifacts/runs/20260211-090054-12.2/`

