# Story 7.4 — Capability gating across mount actions

Implemented capability gating for mount actions so the UI/API do not expose
dead actions:

- Backend adds capability-gated mount action endpoints (`preview`, `wopi`,
  `upload`) that deterministically reject when disabled, and return generic
  no-leak “unavailable” errors otherwise.
- Frontend adds a basic mount browse view and renders actions as hidden when
  capability is false, or disabled with “why + next action” messaging when the
  capability is true but the runtime ability is not available.

## Evidence

- Gates runner report: `run-report.md` / `run-report.json`
- Commands: `commands.log`
- Files changed: `files-changed.txt`

