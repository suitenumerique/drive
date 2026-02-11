# Codex Review + Merge Cycle (repo maintainer)

This file defines the **optimized loop** between:
- the **Codex dev agent** (implements a story in a PR), and
- the **Codex review/maintainer agent** (this conversation) that **verifies**
  evidence, merges, cleans branches, and scaffolds the next stories.

This is meant to be **generic** (not story-specific).

---

## Golden rules

1) **No re-running tests in review mode**
   - The dev agent runs the checks and records results in the run artifacts.
   - The review agent only **verifies** that evidence exists and is coherent.

2) **No-leak**
   - Never paste secrets into PRs, run artifacts, or chat.
   - Avoid echoing full URLs if they might contain sensitive material
     (userinfo/query/keys).

3) **Ignore slow/non-blocking GitHub checks**
   The review agent must **not wait** on these checks:
   - Docker Hub Workflow / build-and-push-backend (push)
   - Docker Hub Workflow / build-and-push-frontend (push)
   - Update crowdin sources / synchronize-with-crowdin (push)
   - Frontend Workflow / test-e2e (chromium|firefox|webkit) (push)

4) **One story = one branch = one PR**
   - PR base must be `main` (avoid stacked PRs).
   - Delete remote branch after merge.

---

## What the dev agent must provide back (message format)

When the dev agent reports completion, it must include:
- PR number + URL
- branch name
- run report path (repo-relative), e.g.
  `_bmad-output/implementation-artifacts/runs/<ts>-<story>/report.md`
- gates summary (PASS/FAIL) as recorded in `gates.md`
- list of commands executed (high-level) and where the full transcript is
  (`commands.log`)
- any known failures / flaky items (with exact error text, no secrets)

The dev agent **must not** ask the review agent to run checks.

---

## Review agent procedure (when user pastes “retour dev”)

### 1) Verify the run artifacts exist and are coherent

From the run folder:
- `report.md` references the correct PR/branch and describes what changed.
- `gates.md` contains the required checks with explicit PASS/FAIL.
- `commands.log` includes the executed commands (safe, no secrets).
- `files-changed.txt` matches `git diff --name-only origin/main..HEAD`.
- `latest.txt` points to this run folder (if it is the most recent run).
- the story file has its **Dev Agent Record** filled and points to the run.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` reflects the story
  state (in-progress → review/done when merged).

### 2) Verify PR status and required checks

Use `gh` to verify:
- PR is against `main`
- PR is mergeable
- Commit messages pass `lint-git` (gitmoji + body, lines ≤ 80)

Do **not wait** on the ignored workflows listed above.

If `CHANGELOG.md` isn’t touched, ensure PR has label `noChangeLog`.
Note: adding the label after a workflow run may not retroactively skip an
already-triggered `check-changelog` job; a new push is the simplest retrigger.

### 3) Merge + cleanup (if everything is OK)

- Merge with `gh pr merge <n> --merge --delete-branch`
  - If CI requirements prevent merging but evidence is correct, use
    `--admin` only when necessary.
- Ensure the remote branch is deleted.
- Confirm `gh api repos/<org>/<repo>/branches` shows no stale branches.

### 4) If not OK: send the dev agent a pasteable fix prompt

Return a short message the user can paste to the dev agent, including:
- what is missing (exact file + what to change)
- which gate is missing or failing
- what to re-run and how to record it
- reminder: no secrets in logs

### 5) If OK: scaffold next story PR(s)

Prepare the next story(ies) by:
- creating the story branch and draft PR
- adding label `noChangeLog` as needed
- creating a prompt under
  `_bmad-output/implementation-artifacts/prompts/<story>-dev.md`

---

## Useful `gh` commands (review mode)

```bash
# PR overview + checks
gh pr view <n> --repo Apoze/drive --json number,state,isDraft,mergeable,headRefName,baseRefName,title,url
gh pr checks <n> --repo Apoze/drive

# Branch inventory
gh api --paginate repos/Apoze/drive/branches --jq '.[].name' | sort

# Merge + delete branch
gh pr merge <n> --repo Apoze/drive --merge --delete-branch
```
