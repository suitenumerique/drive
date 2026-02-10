---
stepsCompleted: [1, 2]
session_continued: true
continuation_date: 2026-02-03T19:33:27+00:00
inputDocuments:
  - _bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md
  - _bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md
  - _bmad-output/planning-artifacts/upstream/drive-open-backlog.md
  - _bmad-output/planning-artifacts/upstream/upstream-triage-v1.md
  - _bmad-output/planning-artifacts/upstream/upstream-triage-v1.yaml
  - (historical) `_bmad-output/planning-artifacts/automation/*` (removed; one-shot orchestrator abandoned)
  - _bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md
  - _bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md
  - _bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md
  - _bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md
  - _bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md
  - (historical) `_bmad-output/planning-artifacts/automation/*` (removed; one-shot orchestrator abandoned)
  - _bmad-output/planning-artifacts/handoff/brainstorming-handoff.md
session_topic: "Poursuivre le développement de Drive (fork MIT) avec une trajectoire self-host upstreamable (Docker/K8s, proxy edge agnostique, S3-first SeaweedFS/Ceph, SMB mount v1, WOPI/Collabora, etc.)"
session_goals: "Respecter les standards upstream (style/structure/tests/CI/conventions PR) tout en intégrant proprement les exigences selfhost via configuration/feature flags/docs/runbooks/packaging, et en visant une chaîne dev+tests+review automatisable de bout en bout"
selected_approach: 'progressive-flow'
techniques_used:
  - Cross-Pollination
  - Constraint Mapping
  - Morphological Analysis
  - Decision Tree Mapping
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Apoze
**Date:** 2026-02-03T11:02:52+00:00

## Session Overview

**Topic:** Poursuivre le développement de Drive (fork MIT) comme produit self-host autonome.
**Goals:** Appliquer des standards internes tout en ajoutant proprement les exigences selfhost, avec un pipeline dev+tests+review robuste.

### Context Guidance

- Contexte lu: `_bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md` (décisions/risques/trajectoire selfhost) et `_bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md` (runbook E2E Playwright + Chrome only).

### Session Setup

- Approche choisie: **Progressive Technique Flow** (phase 1 → 4 : exploration → patterns → développement → action).

## Technique Selection

**Approach:** Progressive Technique Flow (parcours “selfhost + quality gates”)

**Progressive Techniques:**

- **Phase 1 — Expansive Exploration:** `Cross-Pollination` (identifier des patterns réutilisables et “PR-friendly” depuis d’autres projets/self-host réussis)
- **Phase 2 — Pattern Recognition:** `Constraint Mapping` (cartographier contraintes qualité/CI + proxy edge agnostique + OIDC + S3/WOPI + SMB mount + ops)
- **Phase 3 — Idea Development:** `Morphological Analysis` (explorer systématiquement les combinaisons d’options pour converger vers un plan épics/stories clair)
- **Phase 4 — Action Planning:** `Decision Tree Mapping` (séquencer PRs et gates tests pour un delivery itératif)

**Journey Rationale:** On part large (patterns), on contraint (réalité selfhost), on structure (options), puis on transforme en plan d’exécution (PR/tests/review).

## Upstream Intake (Open Backlog Snapshot)

- Snapshot généré à partir de `suitenumerique/drive` (open issues + open PRs).
- Fichier: `_bmad-output/planning-artifacts/upstream/drive-open-backlog.md`

## Automation (Brainstorming Decisions)

- Mode recommandé: **C (Local script + CI)** — script unique pour le dev agent-first + CI pour garantir sur PR.
- Mécanique > subjectif: gates (lint/typecheck/tests/contract tests) + rapport artefacts, puis review LLM *checklist-driven* uniquement.
- S3 contract tests: **Drive-integrated**, “host-first”, avec audiences **INTERNAL/PROXY** vs **EXTERNAL/BROWSER** et séparation `connect_url` vs `signed_host`.

## Upstream Linkage Convention

Objectif: conserver la possibilité d’upstream **sans** en faire une priorité.

- Toute story/ticket local lié upstream porte un champ: `Upstream: https://github.com/suitenumerique/drive/issues/<n>` ou `.../pull/<n>`.
- Les reports/outils doivent conserver au minimum: `upstream_url`, `type` (`issue`/`pr`), `number`, `synced_at`.
