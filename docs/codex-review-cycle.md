# Codex Review + Merge Cycle (repo maintainer)

This file defines the **optimized loop** between:
- the **Codex dev agent** (implements a story in a PR), and
- the **Codex review/maintainer agent** (this conversation) that **verifies**
  evidence, merges, cleans branches, and scaffolds the next stories.

This is meant to be **generic** (not story-specific).

---

## Golden rules

0) **Local files are the source of truth; GitHub PRs are a mirror**
   - Prefer verifying from committed repo artifacts (`_bmad-output/...`) first.
   - Use GitHub checks only to confirm merge requirements are satisfied.

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

5) **Prompt routing (new dev convo vs same dev convo)**
   - If a PR needs fixes, return a pasteable prompt intended for the **same**
     Codex dev conversation that produced the PR (fast context reuse).
   - If everything is OK and you are preparing *new* stories, return a prompt
     intended for a **new** Codex dev conversation (clean context).

6) **Batching (speed)**
   - Dev work is executed in **batches** (multiple stories per dev conversation).
   - Default batch size is **3 stories** (adjust to 2–4 based on scope/risk).
   - Prefer picking the next **contiguous** `ready-for-dev` stories from
     `_bmad-output/planning-artifacts/development-order.md` to minimize churn.
   - Do not stop after the first PR: dev should continue the batch until all
     assigned stories are complete (unless blocked).

---

## What the dev agent must provide back (message format)

When the dev agent reports completion, it must include a single recap message
for the **batch** of stories it worked on (unless blocked), with for each PR:
- PR number + URL
- branch name
- run report path(s) (repo-relative):
  - `.../report.md` (human summary)
  - `.../run-report.md` (gate runner report, if present)
- gates summary (PASS/FAIL) as recorded in `gates.md`
- list of commands executed (high-level) and where the full transcript is
  (`commands.log`)
- any known failures / flaky items (with exact error text, no secrets)

The dev agent **must not** ask the review agent to run checks.

---

## How to prompt the Codex dev agent (templates)

These are **copy/paste** templates you (review/maintainer) can return to the
user to start a **new** Codex dev conversation (new stories) or to request
**fixes** in the **same** dev conversation (existing PRs).

### Template A — New Codex dev conversation (implement a batch)

Replace the placeholders in `<>`. Keep the prompt **story-focused**: reference
the source-of-truth file paths instead of pasting long docs.

```text
Tu es Codex (dev) dans le repo /root/Apoze/drive.

Avant toute action, ouvre et applique :
- docs/codex-agent-baseline.md

Objectif
- Implémenter un batch de <N> stories (2–4, par défaut 3) en suivant STRICTEMENT
  leurs “source de vérité” (_bmad-output/implementation-artifacts/*.md).
- Une branche + une PR par story (base main). Pas de PRs stacked.
- Ne pas attendre les checks GitHub non-bloquants (DockerHub/Crowdin/e2e).
- No-leak: ne jamais mettre de secrets/signed URLs/SigV4/tokens dans diffs/logs.

Stories à faire (dans cet ordre)
1) <story-id> — <story file path>
2) <story-id> — <story file path>
3) <story-id> — <story file path>

Pour CHAQUE story
- Créer une branche `story/<id>-<slug>` + PR vers `main`.
- Faire les changements minimaux (Docker-first, ne pas toucher K8s/Helm).
- Exécuter les vérifs exigées par la story (lint/tests/smokes) et consigner les
  résultats dans les artefacts.
- Traçabilité (si la story l’exige, sinon ne pas inventer) :
  - `_bmad-output/implementation-artifacts/runs/<YYYYMMDD-HHMMSS>-<id>/`
    avec `report.md`, `gates.md`, `commands.log`, `files-changed.txt`.
  - Si présents : `run-report.md` / `run-report.json` (runner).
  - Mettre à jour le “Dev Agent Record” du story file (référence le run).
  - Ne pas modifier `latest.txt` / `sprint-status.yaml` sauf exigence explicite
    de la story (sinon PR “tracking sync” séparée).

Sortie attendue (UN SEUL message, quand tout le batch est terminé)
- Pour chaque PR : numéro + URL, branche, chemin `runs/.../report.md`,
  résumé des gates (PASS/FAIL) tel que dans `gates.md`.
- Signaler tout blocage/FAIL avec le texte exact (no-leak).
```

### Template B — Fixes in-place (same dev conversation / same PRs)

Use this when checks are failing or evidence is missing.

```text
Tu continues dans /root/Apoze/drive sur les PRs/branches déjà ouvertes (ne crée
pas de nouvelles PRs, sauf si demandé explicitement).

Avant toute action, applique :
- docs/codex-agent-baseline.md

Problèmes à corriger (exactement)
1) <PR/branch>: <what failed/missing> — <file/path/gate name>
2) <PR/branch>: <what failed/missing> — <file/path/gate name>

Contraintes
- Fix minimal, no-leak, pas de changements hors scope.
- Si tu modifies l’historique pour réparer `lint-git`, force-push uniquement
  avec `--force-with-lease` et explique dans `report.md` ce qui a changé.

À fournir
- Push les corrections + mise à jour des run artifacts si requis.
- Retourne un récap unique avec l’état final des checks requis (sans attendre
  les workflows non-bloquants).
```

## Review agent procedure (when user pastes “retour dev”)

### 1) Verify the run artifacts exist and are coherent

From the run folder:
- `report.md` references the correct PR/branch and describes what changed.
- If present, `run-report.md` / `run-report.json` match the recorded gates.
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
Also avoid “watching” required checks in a blocking way.

If `CHANGELOG.md` isn’t touched, ensure PR has label `noChangeLog`.
Note: adding the label after a workflow run may not retroactively skip an
already-triggered `check-changelog` job; a new push is the simplest retrigger.

### 3) Merge + cleanup (if everything is OK)

- Prefer auto-merge to avoid idle waiting:
  - `gh pr merge <n> --repo Apoze/drive --auto --merge --delete-branch`
  - Then move on; GitHub will merge when required checks go green.

- If it is already green and you want an immediate merge:
  - `gh pr merge <n> --repo Apoze/drive --merge --delete-branch`
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
- selecting the next items from
  `_bmad-output/planning-artifacts/development-order.md`
- pointing the dev agent at the existing prompt under
  `_bmad-output/implementation-artifacts/prompts/<story>-dev.md`
- assigning a **batch** (default 3 stories) to the dev agent
- avoiding empty “scaffold” PRs with no code changes (create a PR only when
  story work starts), unless there is a concrete repo change needed to unblock.

When merging multiple story PRs:
- Prefer a single “tracking sync” PR to update global tracker files:
  - `_bmad-output/implementation-artifacts/latest.txt`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - story file `Status:` fields (optional, but recommended)
- This avoids repeated merge conflicts across active story branches.

---

## Dev prompt templates (review → dev handoff)

These templates are what the **review/maintainer** should paste to the user,
who then pastes it into the Codex **dev** conversation.

### A) New dev conversation (batch of stories)

Fill the batch list from `_bmad-output/planning-artifacts/development-order.md`
(default: next 3 contiguous `ready-for-dev` stories).

```text
Tu es Codex (dev) dans `/root/Apoze/drive`.

Avant toute action, lis et applique `docs/codex-agent-baseline.md`.

Objectif: terminer ce batch de stories (ne pas s'arrêter après la première) :
- <Story X> — prompt: `_bmad-output/implementation-artifacts/prompts/<X>-dev.md`
- <Story Y> — prompt: `_bmad-output/implementation-artifacts/prompts/<Y>-dev.md`
- <Story Z> — prompt: `_bmad-output/implementation-artifacts/prompts/<Z>-dev.md`

Règles:
- 1 story = 1 branche = 1 PR (base `main`, pas de stacked PRs).
- No-leak strict (aucun secret/URL signée/SigV4/tokens dans logs/diffs/artifacts).
- Ne touche pas `_bmad-output/implementation-artifacts/latest.txt` ni
  `_bmad-output/implementation-artifacts/sprint-status.yaml` dans les PRs story
  (je ferai un tracking sync après merge), sauf si la story l'exige explicitement.
- CI commit-lint: gitmoji valide + body non vide + lignes <= 80.
  Astuce: utilise `git commit -F <file>` (évite les `-m` avec `\\n`).
- `check-changelog`:
  - garde le label GitHub `noChangeLog` tant que la PR est draft/kickoff.
  - quand tu passes une story en ready-for-review: enlève `noChangeLog` et ajoute
    une entrée `CHANGELOG.md` (lignes <= 80).
- Strict mirror (si applicable): le body de la PR doit contenir
  - `Story file: _bmad-output/implementation-artifacts/<story>.md`
  - `BMAD-FP-BP: sha256:...`
  Pour calculer le fingerprint:
  `printf 'Story file: <path>\\n' | python3 bin/strict_mirror_check.py --print`

Traceability (si demandée par la story):
- créer `_bmad-output/implementation-artifacts/runs/<YYYYMMDD-HHMMSS>-<id>/`
  avec `report.md`, `gates.md`, `commands.log`, `files-changed.txt`
  (+ `run-report.*` si généré), et les commit/push dans la branche.
- mettre à jour le story file:
  - `Status: review`
  - section “Dev Agent Record” complétée (pointe vers le run).

Fin de batch uniquement (sauf blocage): envoie un seul récap listant, pour chaque
story: PR + branche + chemin `runs/.../report.md` (+ `run-report.md` si présent)
+ résumé `gates.md` (PASS/FAIL) + risques/notes.
```

### B) Correction d'une PR existante (même conversation dev)

```text
Tu continues dans la MÊME conversation (et sur la même branche/PR).

PR à corriger: <PR #> — branche `<branch>`.

Problème bloquant:
- <résumer précisément le gate qui échoue + le message d'erreur, sans secrets>

À faire:
- <liste d’actions précises, fichiers à modifier, commandes à relancer>
- mettre à jour/compléter les run artifacts si nécessaire (sans no-leak).

Quand c'est corrigé:
- push les commits
- renvoyer un mini récap: PR + check(s) maintenant PASS + run artifact path.
```

## Useful `gh` commands (review mode)

```bash
# PR overview + checks
gh pr view <n> --repo Apoze/drive --json number,state,isDraft,mergeable,headRefName,baseRefName,title,url
gh pr checks <n> --repo Apoze/drive

# Branch inventory
gh api --paginate repos/Apoze/drive/branches --jq '.[].name' | sort

# Merge + delete branch
gh pr merge <n> --repo Apoze/drive --merge --delete-branch

# Auto-merge (recommended to avoid waiting)
gh pr merge <n> --repo Apoze/drive --auto --merge --delete-branch
```
