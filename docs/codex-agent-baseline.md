# Codex Agent Baseline (Drive fork)

This file contains **only** the stable, reusable baseline to run Codex **dev**
work in this repo.

Review/maintainer note:
- This baseline is **primarily** for dev work, but the review/maintainer agent
  should also follow the same no-leak + CI/commit constraints when it creates
  a “tracking sync” PR or any maintainer-side changes.

It must **not** include story-specific instructions (PR numbers, story lists,
or acceptance criteria). Those belong in the per-session text prompt.

## Non-negotiable constraints

- **Docker-first**: prefer compose-path changes; keep changes minimal.
- **Do not remove/modify existing K8s/Helm assets**: they stay reference-only.
- **Do not add out-of-scope features**:
  - Implement only what the story asks for (AC/tasks).
  - Avoid opportunistic refactors or UI/UX changes unless explicitly required.
  - If a dependency is missing (e.g. a provider not implemented yet), implement
    only the deterministic contract surface and keep runtime behavior safe.
- **No-leak** (mandatory):
  - Never put secrets in diffs, docs, artifacts, or logs.
  - Do not paste signed URLs, SigV4 headers, credentials, tokens, or secret refs.
  - Avoid printing raw object keys/paths if they could be sensitive; prefer hashes.
- **Fail-fast validation** when a story requires it:
  - Deterministic `failure_class` + `next_action_hint`.
  - Error messages must be actionable and must not echo sensitive inputs.

## Tooling available (Codex dev environment)

- `git` is available (branching/commits/merge-from-main/push).
- GitHub CLI `gh` is available and may be used when it helps:
  - Create/update PRs (`gh pr create`, `gh pr edit`, `gh pr view`, `gh pr checks`)
  - Manage labels (e.g. add `noChangeLog` early)
  - Confirm required checks are green (do not wait on non-blocking checks)

If `gh` or `git push` fails due to auth/permissions:
- Record the exact error text in the run artifacts (no secrets).
- Stop and report the blocker (do not claim “pushed” / “PR updated”).

## Branching / PR workflow (speed + safety)

- **One story = one branch + one PR**.
- PR base must be `main` (avoid stacked PRs).
- Treat PRs as a **mirror** of the repo-local source of truth:
  - project communication and traceability live under `_bmad-output/...`
  - PRs exist to sync/track that work on GitHub
- Keep the repo clean:
  - After merge, delete the remote branch.
  - Avoid long-lived “work in progress” branches without a PR.

## Verification (dev-run)

The Codex dev agent runs the required lint/tests/smoke and records results in
the story run report. No secrets in logs/artifacts.

The dev agent should stop at “ready for review” for each story, but should
only send a recap message once the **assigned batch** of stories is complete
(unless blocked). Merging is handled by the review/maintainer loop.

Default batch size is **3 stories** (adjust to 2–4 based on scope/risk).

Do **not** wait for GitHub checks to complete before continuing work. GitHub is
treated as a mirror; your “PASS” evidence is what you ran and recorded in the
run artifacts.

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
- Add the `noChangeLog` label **before** expecting CI to pass. If CI already ran
  without it, push a follow-up commit to retrigger checks after adding the label.

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

Some stories and tools also use a **gate runner report**:
- `run-report.md` and `run-report.json` (machine-oriented, deterministic)

Rule of thumb:
- Always include `report.md` (human summary).
- If you run gates via a runner that produces `run-report.*`, commit them too,
  and have `report.md` link to `run-report.md`.
- `git add` + commit + push the run folder (and any pointer/status updates),
  so reviewers can verify them from the PR.
- Always update (per-story, low-conflict):
  - The story file “Dev Agent Record” section (points to the run folder)

Global tracker files (high-conflict; prefer batching):
- `_bmad-output/implementation-artifacts/latest.txt`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

Preferred approach:
- Do **not** touch the global tracker files in every story PR.
- Instead, do a separate “tracking sync” PR that updates `latest.txt` and
  `sprint-status.yaml` after a batch of story PRs is merged.

If a specific story explicitly requires updating the global tracker files:
- Keep those edits in a **single final commit** (easier conflict resolution).

If your PR becomes `CONFLICTING` after other merges:
- Prefer a **merge-from-main** commit (no force-push): `git fetch origin` then
  `git merge origin/main`, resolve conflicts, commit, push.
- Conflicts commonly happen in shared tracker files like `latest.txt` and
  `sprint-status.yaml`.
