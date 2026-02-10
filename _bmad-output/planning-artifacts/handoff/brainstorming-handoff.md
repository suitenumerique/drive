# Brainstorming Handoff — BMAD v6 (to PM / Planning)

## Purpose

Hand off the brainstorming outputs for `Apoze/drive` so the next BMAD v6 agent (PM / Planning) can produce:

- a consolidated PRD
- a final executable BMAD registry (items with stable IDs, dependencies, gates, test checklists)

## Non‑negotiables (decisions)

- **Repo scope:** work happens only in `Apoze/drive`. Agents must not interact with `suitenumerique/drive` (no read/write).
- **Upstream:** only a **local snapshot** is used for reference; no refresh by agents.
- **Source of truth:** BMAD registry/artifacts. GitHub issues/PRs on `Apoze/drive` are a **strict mirror**.
- **Strict mirror enforcement:** issue/PR bodies include a **fingerprint (B+)** computed from:
  - `area`, `kind`, `priority`, `depends_on`
  - `acceptance_criteria`, `gates`, `test_checklist`
  - excludes dynamic fields (`status`, `gh.*`, runs, timestamps, notes)
- **S3 model:** Drive-integrated contract tests with explicit audiences:
  - INTERNAL/PROXY vs EXTERNAL/BROWSER
  - `connect_url` vs `signed_host`
- **E2E:** Chrome-only (host-first), artifacts retained.
- **No‑leak:** reports/artefacts must avoid raw keys/paths/credentials (hash + reason codes only).

## Core artifacts (inputs)

### Upstream snapshot (local, frozen)

- `_bmad-output/planning-artifacts/upstream/drive-open-backlog.md`
- `_bmad-output/planning-artifacts/upstream/drive-open-issues.json`
- `_bmad-output/planning-artifacts/upstream/drive-open-prs.json`

### Automation / agent autonomy

Archived: the historical “skills/orchestrator/strict mirror” plan was abandoned. Current work relies on normal development workflow + Make targets for checks, while keeping `_bmad-output/` as a local knowledge base.

### Storage (MountProvider + SMB v1)

- `_bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md`
- `_bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md`
- `_bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md` (Filestash-like approach as inspiration)
- Sources (archived):
  - `_bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md`
  - `_bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md`

### Packaging (selfhost)

- `_bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md`

### WOPI / Collabora

- `_bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md`

## Recommended next steps (PM / Planning)

1) **Create PRD**
   - Consolidate goals/scope per axis: Storage, Automation, Packaging, WOPI.
   - Define v1/v2 scope and explicit non-goals.
   - Capture risks and validation plan (contract tests, e2e, restore test).

2) **Create a lightweight backlog**
   - Convert draft stories into GitHub issues (fork repo only), or a simple markdown list under `_bmad-output/`.
   - Keep Acceptance Criteria close to the issue/story and validate via Make targets (`make lint`, `make test-back`, etc.).

3) **Handoff to implementation**
   - Implement iteratively via normal development workflow and Codex conversations (dev/test/debug/review), without a strict-mirror orchestrator.

## Session index

- Brainstorming session state: `_bmad-output/brainstorming/brainstorming-session-20260203-110252.md`
