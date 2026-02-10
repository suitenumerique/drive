# Codex Agent Baseline (Drive fork)

This file is the canonical, reusable baseline to run Codex dev work in this repo.
New prompts should reference this file instead of repeating the same constraints.

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
- **Stacked PRs are allowed** when there is a strict dependency:
  - Branch B can target branch A.
  - After A merges, rebase/retarget B onto `main`.
- Keep the repo clean:
  - After merge, delete the remote branch.
  - Avoid long-lived “work in progress” branches without a PR.

## Verification ownership (dev-run)

Per operator instruction for this fork:
- The **developer (human) runs lint/tests/smoke** and records the results in the
  story run report.
- The agent must **not** run those checks “to validate”; it may only read the
  report and ensure the results are present and consistent.

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
- Update:
  - `_bmad-output/implementation-artifacts/latest.txt`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - The story file “Dev Agent Record” section

