# Architecture Kickoff Brief (for BMAD v6 Architect)

## Context

Repository: `Apoze/drive` (this is the primary repo for the project).

Agents must not interact with upstream `suitenumerique/drive` (no read/write). Upstream is referenced only via a frozen local snapshot.

This brief exists to accelerate the Architect phase. It is not a replacement for the final architecture document.

## Status (planning)

- The PRD is finalized at: `_bmad-output/planning-artifacts/prd.md` (treat as the source of truth for product requirements).
- A v1 upstream snapshot triage (local, frozen) is available at:
  - `_bmad-output/planning-artifacts/upstream/upstream-triage-v1.md`
  - `_bmad-output/planning-artifacts/upstream/upstream-triage-v1.yaml`

## Goals (architectural)

1) Keep Drive coherent and maintainable while adding major selfhost capabilities:
   - MountProvider framework + SMB mount v1 (upload/preview/share links/WOPI)
   - Packaging baseline (Nginx edge, `DRIVE_PUBLIC_URL`, TLS strategy, backup/restore, upgrade/rollback)
   - Automation baseline (agent-operable loop: preflight → gates → artifacts → strict mirror)

2) Preserve the option to upstream later (human decision), by:
   - preferring provider-neutral, capability-driven boundaries
   - keeping PRs small and boundaries clear

## Non‑negotiables / system constraints

- Repo scope: `Apoze/drive` only.
- Source of truth: BMAD registry/artifacts.
- GitHub issues/PRs are strict mirrors (fingerprint B+) of registry requirements.
- No-leak: generated reports must not contain raw S3 keys, SMB paths, or credentials.
- E2E: Chrome-only, host-first.
- Storage: explicit audiences (INTERNAL/PROXY vs EXTERNAL/BROWSER) where relevant; `connect_url` vs `signed_host` separation for S3 contract logic.

## Existing codebase landmarks (important)

- Django/DRF backend with `/api/v1.0/...` routes.
- `media-auth` is a contract point (Nginx `auth_request` + SigV4 headers).
- S3 logic currently spans `default_storage` + direct boto3 client usage in API/tasks; a boundary is planned.

## Architecture decisions needed (deliverables)

### A) Codebase “domain map” & boundaries

Deliver:

- where storage logic belongs (e.g. `core/storage/`)
- where mount logic belongs (MountProvider interface, SMB provider)
- where WOPI logic belongs (per-backend capability, locks, version string)
- where automation tooling belongs (scripts, registry schema, CI checks)

### B) Naming + conventions

Deliver conventions for:

- modules and packages (Python)
- DRF viewsets/actions naming and routing
- error handling patterns (e.g. `media-auth` stays opaque with 403)
- capability naming (stable keys, documented)
- failure_class naming (stable taxonomy)

### C) API patterns (consistency)

Deliver:

- consistent pagination rules for mount browsing
- streaming vs buffering rules for uploads/downloads
- how to represent “virtual entries” (mount_id + path) in API responses
- safe logging rules (no raw paths)

### D) Extension points (plugin-like)

Deliver:

- MountProvider interface: minimal operations required by SMB v1
- Capability-driven feature activation (UI + API)
- Versioning prereqs for WOPI:
  - S3: requires bucket versioning
  - SMB: uses application version string + locks

## Inputs (read these first)

Handoff:

- `_bmad-output/planning-artifacts/handoff/brainstorming-handoff.md`
- `_bmad-output/planning-artifacts/prd.md`

## Process requirement (handoff discipline)

- Do **not** edit `_bmad-output/planning-artifacts/handoff/brainstorming-handoff.md` (it is the frozen brainstorming record).
- After finishing the architecture pass, produce a new handoff for PM:
  - `_bmad-output/planning-artifacts/handoff/architect-handoff.md`
  - Must include: architecture decisions summary, test strategy notes, and conventions to apply (naming/API/logging/no-leak).

Storage (MountProvider + SMB v1 + tests):

- `_bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md`
- `_bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md`
- `_bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md`

Packaging:

- `_bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md`

WOPI:

- `_bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md`

Archived sources (context only):

- `_bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md`
- `_bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md`

## Skill plan (status)

Deprecated: a “skills per epic” plan was considered, but the repo no longer targets a skills-based execution layer.

Current approach:

- Implement features via normal development workflow and Codex conversations.
- Run checks via Make targets (e.g. `make lint`, `make test-back`, `make frontend-lint`, `make run-tests-e2e`).

## Open questions for the Architect

1) Where exactly should MountProvider live in the backend package tree (to avoid future refactors)?
2) What is the canonical representation for mount entries (IDs vs path encoding)?
3) How should mount browsing pagination and sorting be standardized?
4) What is the minimal, stable capability set needed for v1?
5) What is the lock manager design for SMB WOPI (DB-backed vs Redis-backed) under selfhost constraints?
