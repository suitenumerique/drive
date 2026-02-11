# Gates runner (stable `gate_id`, deterministic artifacts)

Drive’s deterministic gates runner executes repo checks via stable `gate_id`s
and writes machine-readable artifacts under `_bmad-output/implementation-artifacts/`.

## Run

- Infer gates from diff:
  - `bin/agent-check.sh`
- Explicit gates:
  - `bin/agent-check.sh --gate backend.lint --gate backend.tests`
- Preflight (resolve only, no execution):
  - `bin/agent-check.sh --preflight --gate backend.lint`
- Tag the run folder (useful for stories/PRs):
  - `bin/agent-check.sh --tag 12.1 --gate backend.lint`

## Gate catalog

List available gates:

`bin/agent-check.sh --list-gates`

## Artifacts

Each run writes:

- `_bmad-output/implementation-artifacts/runs/<run_id>/run-report.md`
- `_bmad-output/implementation-artifacts/runs/<run_id>/run-report.json`
- `_bmad-output/implementation-artifacts/runs/<run_id>/gates/gate-results.json`
- `_bmad-output/implementation-artifacts/latest.txt` (relative pointer)

If `no_leak.scan_bmad_output` is executed, it also writes:

- `_bmad-output/implementation-artifacts/runs/<run_id>/gates/no_leak.scan_bmad_output.evidence.json`

