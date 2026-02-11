# Story 2.5: Docker-first upgrade/rollback runbook + deterministic post-action smoke checklist

Status: done

## Story

As an operator,
I want documented, Docker-first upgrade and rollback procedures with a deterministic post-action smoke checklist,
So that I can apply updates safely and recover quickly if something goes wrong, without ambiguity or leaks.

## Acceptance Criteria

**Given** I operate the Docker-first deployment  
**When** I follow the upgrade runbook  
**Then** it provides concrete, step-by-step instructions that make ordering explicit (e.g., pin/pull images → run migrations → restart services → smoke checks), plus prerequisites and safety notes, without leaking secrets.

**Given** an upgrade fails or must be reverted  
**When** I follow the rollback runbook  
**Then** it provides concrete, step-by-step instructions to rollback to a known-good state, including DB/object storage compatibility notes, and clarifies that rollback may require DB restore if migrations are not backward-compatible, without leaking secrets.

**Given** an upgrade or rollback completed  
**When** I execute the post-action smoke checklist  
**Then** it includes at least these deterministic checks (with expected outcomes):
- login succeeds (operator-provided external OIDC IdP; Keycloak only if used as a dev fixture),
- browse a workspace/folder succeeds,
- open an existing file preview works or shows a clear, actionable state (no infinite loading; no-leak),
- upload succeeds (or fails with an actionable no-leak error),
- media access via the `/media` flow succeeds (or fails with an actionable no-leak error referencing the edge contract).  
**And** if public share links are enabled for the environment, opening an existing share link works or shows a clear, actionable no-leak state; if a mount-backed share link is tested, it respects the 404/410 semantics for MountProvider targets.

## Tasks / Subtasks

- [ ] Write upgrade runbook (AC: 1)
  - [ ] Explicit ordering (pin/pull → migrate → restart → smoke)
  - [ ] Prereqs and safety notes (no-leak)
- [ ] Write rollback runbook (AC: 2)
  - [ ] Rollback ordering + compatibility notes
  - [ ] DB restore requirement note for non-backward-compatible migrations
- [ ] Write deterministic post-action smoke checklist (AC: 3)
  - [ ] Login
  - [ ] Browse
  - [ ] Preview
  - [ ] Upload
  - [ ] `/media` flow
  - [ ] Optional: public share link + mount-backed 404/410 semantics check
- [ ] Verification (doc quality)
  - [ ] Ensure steps are concrete and do not assume Kubernetes.
  - [ ] Ensure examples do not contain secrets.

## Dev Notes

- Docker-first procedures should be compatible with the project’s compose-based baseline.
- Keep rollback expectations explicit: “may require DB restore” must be unambiguous.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.5 Acceptance Criteria]
- [Source: `_bmad-output/project-context.md` — `/media` contract and dev fixtures notes]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260211-084234-2.5/report.md`

### Completion Notes List

- Added Docker-first upgrade and rollback runbooks with explicit ordering.
- Documented rollback safety: DB restore may be required after migrations.
- Expanded the deterministic post-action smoke checklist to include required
  PASS/FAIL outcomes (login/browse/preview/upload/media/share).

### File List

- `docs/selfhost/upgrade.md`
- `docs/selfhost/rollback.md`
- `docs/selfhost/smoke-checklist.md`
- `docs/selfhost/README.md`
- `docs/installation/README.md`
- `CHANGELOG.md`
- `_bmad-output/implementation-artifacts/runs/20260211-084234-2.5/report.md`
