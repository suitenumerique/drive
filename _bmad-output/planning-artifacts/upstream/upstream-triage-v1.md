# Upstream triage (v1) — notes

This document is a lightweight triage of upstream `suitenumerique/drive` signals (issues/PRs) used as **reference input** during planning.

- Snapshot sources are kept under this folder (see `drive-open-backlog.md`, `drive-open-issues.json`, `drive-open-prs.json`).
- This is **not** a requirement to upstream changes; it exists to preserve context about upstream behavior and constraints that informed `Apoze/drive` planning.

## Triage goals

- Identify upstream-relevant constraints (packaging, auth, storage, UX patterns) that should be treated as local constraints to reduce rework.
- Extract “known drifts / gaps” to validate early (e.g., share UX completeness, proxy/media edge behavior).

## Notes

- Keep this document short and stable; detailed planning lives in `_bmad-output/planning-artifacts/prd.md`, `_bmad-output/planning-artifacts/architecture.md`, and `_bmad-output/planning-artifacts/ux-design-specification.md`.

