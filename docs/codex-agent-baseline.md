# Codex Agent Baseline (Drive fork)

This file contains **only** the stable, reusable baseline to run Codex **dev**
work in this repo.

It must **not** include story-specific instructions (PR numbers, story lists,
or acceptance criteria). Those belong in the per-session text prompt.

## Non-negotiable constraints

- **Docker-first**: prefer compose-path changes; keep changes minimal.
- **Do not remove/modify existing K8s/Helm assets**: they stay reference-only.
- **No-leak** (mandatory):
  - Never put secrets in diffs, docs, artifacts, or logs.
  - Do not paste signed URLs, SigV4 headers, credentials, tokens, or secret refs.
  - Avoid printing raw object keys/paths if they could be sensitive; prefer hashes.
- **Fail-fast validation** when a story requires it:
  - Deterministic `failure_class` + `next_action_hint`.
  - Error messages must be actionable and must not echo sensitive inputs.

## Branching / PR workflow (speed + safety)

- **One story = one branch + one PR**.
- PR base must be `main` (avoid stacked PRs).
- Keep the repo clean:
  - After merge, delete the remote branch.
  - Avoid long-lived “work in progress” branches without a PR.

## Verification (dev-run)

The Codex dev agent runs the required lint/tests/smoke and records results in
the story run report. No secrets in logs/artifacts.

The dev agent should stop at “ready for review” and report back; merging is
handled by the review/maintainer loop.

**Important**: do not claim “PASS” unless the evidence is **committed and
pushed** in the PR branch (run folder + updated pointers). Local-only runs are
not verifiable and will be treated as missing.

## Commit conventions (CI blockers)

- Commit title format must be valid gitmoji:
  - `<emoji>(<scope>) <subject>`
- Commit body requirements:
  - **Non-empty body**.
  - **Every line <= 80 characters** (avoid `\n` literals in `-m`).

## CHANGELOG / check-changelog gate

- PRs must update `CHANGELOG.md` unless the PR has label `noChangeLog`.
- For scaffolds (prompts/status-only), prefer label `noChangeLog`.

## GitHub checks: blocking vs non-blocking

Do not wait for the following workflows/checks (treated as non-blocking here):
- Docker Hub Workflow / build-and-push-backend (push)
- Docker Hub Workflow / build-and-push-frontend (push)
- Update crowdin sources / synchronize-with-crowdin (push)
- Frontend Workflow / test-e2e (chromium) (push)
- Frontend Workflow / test-e2e (firefox) (push)
- Frontend Workflow / test-e2e (webkit) (push)

## Traceability (required by stories using run reports)

When a story requires traceability artifacts, follow the story’s exact format:
- Create `_bmad-output/implementation-artifacts/runs/<ts>-<story>/` with:
  - `report.md`, `commands.log`, `files-changed.txt`, `gates.md`
- `git add` + commit + push the run folder (and any pointer/status updates),
  so reviewers can verify them from the PR.
- Update:
  - `_bmad-output/implementation-artifacts/latest.txt`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - The story file “Dev Agent Record” section
