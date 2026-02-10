---
workflow: create-ux-design
project_name: drive
author: Apoze
date: "2026-02-04T00:05:36+00:00"
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
lastStep: 14
inputDocuments:
  - _bmad-output/planning-artifacts/architecture/architecture-kickoff-brief.md
  - _bmad-output/planning-artifacts/handoff/brainstorming-handoff.md
  - _bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-drive-20260203-200136.md
  - _bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md
  - _bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md
  - _bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md
  - _bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md
  - _bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md
  - _bmad-output/planning-artifacts/upstream/drive-open-backlog.md
  - _bmad-output/planning-artifacts/upstream/upstream-triage-v1.md
  - _bmad-output/planning-artifacts/validation-report-prd-20260203-234119.md
  - _bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md
  - docs/architecture.md
  - docs/ds_proxy.md
  - docs/entitlements.md
  - docs/env.md
  - docs/installation/README.md
  - docs/installation/kubernetes.md
  - docs/metrics.md
  - docs/release.md
  - docs/resource_server.md
  - docs/setup-find.md
  - docs/theming.md
  - src/frontend/apps/drive/src/features/layouts/components/explorer/ExplorerLayout.tsx
  - src/frontend/apps/drive/src/features/layouts/components/global/GlobalLayout.tsx
  - src/frontend/apps/drive/src/features/layouts/components/header/Header.tsx
  - src/frontend/apps/drive/src/features/ui/cunningham/useCunninghamTheme.ts
  - src/frontend/apps/drive/src/pages/401.tsx
  - src/frontend/apps/drive/src/pages/403.tsx
  - src/frontend/apps/drive/src/pages/_app.tsx
  - src/frontend/apps/drive/src/pages/_document.tsx
  - src/frontend/apps/drive/src/pages/explorer/items/[id].tsx
  - src/frontend/apps/drive/src/pages/explorer/items/files/[id].tsx
  - src/frontend/apps/drive/src/pages/explorer/items/public.tsx
  - src/frontend/apps/drive/src/pages/explorer/items/shared.tsx
  - src/frontend/apps/drive/src/pages/explorer/trash/index.tsx
  - src/frontend/apps/drive/src/pages/index.tsx
  - src/frontend/apps/drive/src/pages/sdk/explorer/index.tsx
  - src/frontend/apps/drive/src/pages/sdk/index.tsx
  - src/frontend/apps/drive/src/styles/cunningham-tokens-sass.scss
  - src/frontend/apps/drive/src/styles/cunningham-tokens.css
  - src/frontend/apps/drive/src/styles/globals.scss
  - src/frontend/apps/sdk-consumer/src/App.tsx
  - src/frontend/apps/sdk-consumer/src/main.tsx
---

# UX Design Specification drive

**Author:** Apoze
**Date:** 2026-02-04T00:05:36+00:00

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

### Project Vision

`drive` (Apoze/drive) vise une expérience “Drive” self-hosted **production-usable** où l’utilisateur final peut **naviguer, uploader, prévisualiser, partager et ouvrir en WOPI** de façon fiable — quel que soit l’environnement — grâce à un contrat clair entre navigateur/proxy/S3 (INTERNAL/PROXY vs EXTERNAL/BROWSER) et des diagnostics déterministes.

Identity est **bring-your-own OIDC IdP** : les déploiements production ne fournissent pas d’IdP.

La v1 doit préserver un **S3-first core** stable (pas de régression) tout en introduisant un différenciant majeur : une extensibilité storage via **MountProvider** (SMB mount v1) — sans complexifier ni casser les parcours S3.

Le design doit rester dans le **style existant** (existing design system / UI kit / tokens), avec une approche **capability-driven** : aucune action “morte”, seulement des actions activées quand le backend/prérequis le permettent, sinon un état “Feature not enabled” + renvoi doc/runbook.

### Target Users

- **End users (knowledge workers)** : explorer/browse, upload, preview, share links, entrée WOPI (quand disponible).
- **Self-host operators** : config fiable, runbooks, smoke checks, diagnostics actionnables sans leaks.
- **SRE / intégrateurs** : BYO OIDC, reverse proxy constraints, resource server/entitlements/metrics/theming.
- **Support / on-call** : triage rapide via `failure_class` + “safe evidence” (request_id/status codes/hashes), sans secrets ni chemins sensibles.

### Key Design Challenges

- **Fiabilité perçue** sur les parcours critiques (upload/preview/share/WOPI) malgré la complexité proxy/S3.
- **Deux audiences storage** (INTERNAL/PROXY vs EXTERNAL/BROWSER) : rendre les échecs compréhensibles pour l’opérateur sans exposer d’informations sensibles.
- **Capabilités & prérequis** (WOPI, mounts, diagnostics) : éviter les boutons morts, proposer des états “disabled” explicites et des messages orientés action (next_action_hint).
- **Desktop-first** mais “responsive no regressions” : mobile/tablette doivent rester utilisables pour les actions basiques (browse/download/open share link).
- **Accessibilité** : WCAG 2.1 AA “no regressions”, + 2–3 améliorations visibles et cadrées sur des parcours critiques.

### Design Opportunities

- **Trust & feedback** : renforcer le feedback d’upload (progress, erreurs, reprise), et la clarté des états share/WOPI (loading, erreurs, permissions).
- **Operator Diagnostics — “Storage & Proxy Health”** : une vue dédiée pour CT-S3, /media contract, quick diagnostics, et génération d’un support bundle **no-leak**.
  - Diagnostics doivent exposer `failure_class` + safe evidence et refléter explicitement les audiences INTERNAL/PROXY vs EXTERNAL/BROWSER.
  - Options de placement (compatibles style existant) :
    - (A) nouvelle route “Settings/Diagnostics” (propre, scalable)
    - (B) intégration légère : “Diagnostics” dans l’Explorer (right panel) ou via un menu “Help/Troubleshooting”
- **Mount Secrets & Rotation (SMB/MountProvider)** : UX de secrets par référence (jamais le password), actions “Validate connection” + “Refresh/Re-check”, et statuts “configured / last refresh / last successful auth”.
- **A11y ciblée (3 cibles explicites)** :
  - navigation clavier + focus dans Explorer (tree + list)
  - focus management + aria dans les modales share/WOPI
  - feedback upload (progress + errors) lisible et accessible (announcements)
- **Note d’implémentation à confirmer** : placeholder content détecté dans `FileShareModal.tsx` suggère que des parties de l’UX “file sharing” peuvent être inachevées ; à confirmer selon le comportement v1 attendu et la readiness backend.

## Core User Experience

### Defining Experience

La boucle principale de Drive est : **je trouve le bon fichier/dossier → j’agis dessus (upload/preview/share/WOPI) → je reviens exactement au même contexte** (même dossier, même sélection, même vue).

Le produit se vit avant tout dans l’Explorer : navigation (tree + liste), actions contextualisées (menus/modales/panneaux), et retours immédiats (progress, erreurs, confirmations) sans “sauter” l’utilisateur vers un autre endroit ou lui faire perdre le fil.

### Platform Strategy

- **Web app desktop-first** (mouse + modales) : l’expérience v1 doit être solide et prévisible sur desktop, sans exiger des comportements “power user” (au-delà des exigences a11y de base).
- **Responsive no-regressions** : mobile/tablette doivent rester utilisables pour les actions basiques :
  - ouvrir un share link et voir le fichier (ou un état d’erreur clair)
  - télécharger un fichier (ou ouvrir via le viewer système)
  - upload sur mobile : “best effort / no regressions”, pas une garantie v1
- **WOPI/Collabora** : disponible quand activé et fonctionnel dans le navigateur ; pas de promesse “mobile app” v1.

### Effortless Interactions

1) **Upload (priorité #1)** — doit être fiable, explicite et récupérable :
   - progression visible, états clairs (préparation/création dossiers/upload en cours/terminé)
   - en cas d’échec : message actionnable + option de retry/reprise quand possible, jamais une disparition silencieuse
   - ne pas perdre le contexte (le user reste dans son dossier, la liste se met à jour)

2) **Find / Navigate (priorité #2)** — doit préserver le contexte :
   - navigation fluide entre dossiers/workspaces
   - après actions (upload/rename/share/WOPI retour), restaurer dossier + sélection + position de scroll (quand faisable)

3) **Preview (priorité #3)** — rapide et prévisible :
   - loading explicite, erreurs non ambiguës
   - si preview indisponible : fallback clair (ex: download / info)

4) **Share / WOPI entry (priorité #4)** — légèrement plus guidé acceptable, mais états impeccables :
   - permissions/capabilités explicites (capability-driven)
   - états “opening/connecting/error” clairs pour éviter “endless loading”

### Critical Success Moments

- **Moment “trust” v1** : un upload qui réussit avec feedback clair, sans perte de contexte.
- **Moment “confidence”** : preview/WOPI fonctionne, ou bien affiche un état clair + prochaine action (pas de loading infini, pas d’échec silencieux).
- **Moment “share” (MountProvider share links)** : l’UX distingue explicitement :
  - `404` = token invalide/inconnu
  - `410` = token connu mais cible absente (déplacée/supprimée)
- **Make-or-break** : toute perte de contexte après action (workspace/dossier/sélection/vue) est une régression majeure.

### Experience Principles

- **Reliability-first** : upload/preview/WOPI doivent être robustes et diagnosables côté utilisateur (messages actionnables).
- **Context-preserving** : aucune action ne doit “désorienter” ; retour au même contexte par défaut (dossier + sélection + position de scroll, quand faisable).
- **Clear state always** : loading/errors explicites, jamais d’ambiguïté.
- **Capability-driven UX** : pas d’actions mortes ; si non activé → “Feature not enabled” + lien doc/runbook.
- **No-leak by design** : aucun secret/chemin sensible dans les messages ou artefacts visibles.
- **Accessibility baseline** : WCAG 2.1 AA no-regressions + focus/keyboard corrects sur les parcours critiques.

## Desired Emotional Response

### Primary Emotional Goals

**Primary goal: Trust (Confiance).**

- **End-user trust:** “My file is uploaded, visible, and safe. I can act on it without fear.”
- **Operator trust:** “This holds in production. When it breaks, it’s diagnosable without leaks.”

### Emotional Journey Mapping

- **First encounter / first use:** clarity and reassurance (“this is predictable; I understand what will happen”).
- **During the core loop (find → act → return):** in control and anchored (“I know where I am; the UI keeps my context”).
- **After success (upload complete / action done):** relief + confidence (“done, visible, safe”).
- **When something goes wrong (upload/preview/WOPI):** calm + informed + in control (“clear status, clear next action; no silent failure”).
- **Returning later:** continuity and orientation (“same context; I don’t have to re-find my place”).

### Micro-Emotions

Critical micro-emotions to reinforce:
- **Confidence over anxiety** (“my file is not lost”).
- **Clarity over confusion** (no ambiguous states / no infinite loading).
- **Trust over skepticism** (no-leak posture; sharing feels controlled).
- **Control over helplessness** (actionable errors + recovery path).
- **Anchored over disoriented** (context preserved after actions).

Emotions to avoid (hard constraints):
- Anxiety (“is my file lost?”)
- Confusion (ambiguous states / endless loading)
- Skepticism (fear of leak / uncontrolled sharing)

### Design Implications

To create **Trust**, the UX must:
- Always show an explicit **state model** for long/fragile operations (upload, preview, WOPI): loading/progress, success confirmation, error with explanation.
- **No infinite loading:** loading states must be **time-bounded**; if an operation exceeds a threshold, the UI must switch to a “still working / retry / contact admin” state instead of spinning indefinitely.
- Prefer **actionable failure**: every failure leads to a clear next action (retry, download, re-open, contact admin, link to doc/runbook).
- Preserve **context** after actions (folder + selection + view; scroll position when feasible) to keep users anchored.
- Make **capabilities explicit** (capability-driven): if WOPI/share/mount feature isn’t enabled or available, show “Feature not enabled” + guidance instead of dead actions.
- Enforce **no-leak by design** in user-visible messaging and operator outputs: surface only safe evidence (e.g., request_id, status codes, hashes) and stable failure classification.

To create **Operator reassurance / control**, diagnostics must:
- Reflect INTERNAL/PROXY vs EXTERNAL/BROWSER audiences.
- Surface `failure_class` + safe evidence, and support “support bundle” style exports without secrets/paths.
- Guidance must stay **proxy-agnostic**: it should describe required **edge contracts**, not prescribe a single reverse proxy implementation.

### Emotional Design Principles

- **Trust is the UI’s default posture**: explicit states, explicit outcomes.
- **Clarity beats cleverness**: no silent transitions, no ambiguous waiting.
- **Control through guidance**: errors always include a next step.
- **Context is sacred**: don’t disorient users; keep them anchored.
- **No-leak is non-negotiable**: trust collapses if leaks are suspected.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

**OneDrive (web)**
- Strong context-preserving explorer: coherent back/forward behavior, clear breadcrumbs, actions (rename/share/move) do not “teleport” the user.
- Share/open flows feel explicit: share-link pages are clean; states distinguish “no access” vs “not found”; preview/opening is usually status-driven.

**Google Drive**
- Upload feedback is best-in-class: queue, progress, actionable errors, and recovery/resume without losing context.
- Sharing is simple and readable: clear link modes (public/restricted), who has access, and clean return to the explorer.

**Dropbox**
- Perceived reliability through explicit state language: “syncing / up to date / failed” style signaling (even in a web-first context, the principle transfers).
- Share links are frictionless: easy copy, clean link pages, predictable behavior.

**GitHub (web UI)**
- Non-ambiguous state model everywhere: pending/success/fail with action-oriented messaging.
- Diagnostics without leaks: error/permission surfaces are structured and useful; artifacts/log-like outputs are safe and actionable (good inspiration for operator UX).

### Transferable UX Patterns

**Navigation & Context Preservation**
- Breadcrumbs as the “anchor” + coherent back/forward behavior.
- After an action, return to the same context by default (folder + selection + view; scroll position when feasible).
- Avoid full-page jumps for small actions; prefer contextual surfaces (modal / side panel) when consistent with the app.

**State Clarity (No Ambiguity)**
- A consistent state vocabulary: loading → success → failure, with stable, user-readable meanings.
- **No infinite loading**: time-bounded loading that degrades into “still working / retry / contact admin” instead of spinning indefinitely.
- Errors always include a next step (retry, download, re-open, check permissions, link doc/runbook).

**Upload Reliability & Recovery**
- Upload as a first-class flow: visible queue/progress, clear completion, explicit failure with retry/resume when feasible.
- Recovery/resume is backend-dependent: **S3 uploads are browser presigned**, while **MountProvider/SMB uploads are backend‑mediated streaming**, so retry/resume behavior must be specified per backend/provider (when feasible), not assumed universal in v1.
- Preserve context during upload: user stays in place; new items appear predictably; failures don’t “disappear”.

**Sharing & Link Pages**
- Link pages should be clean and explicit about what’s happening (open/view/download) and why it might fail.
- Clear distinction between permission vs not-found style outcomes (with special semantics for MountProvider shares as defined in the PRD).
- For **MountProvider links**, `410` means the link token is valid but the target was moved/deleted out-of-band; the UX must explain this cleanly.

**Operator/Support Surfaces (GitHub-inspired)**
- Structured “health” status: green/yellow/red style summaries backed by actionable detail.
- Outputs must be no-leak and safe evidence–based (e.g., request_id/status/hashes), aligned with INTERNAL/PROXY vs EXTERNAL/BROWSER audiences.
- Guidance remains proxy-agnostic: describe edge contracts, not a single reverse proxy implementation.

### Anti-Patterns to Avoid

- Infinite loading / ambiguous states (no “still working”, no next action, silent failures).
- Dead buttons or disabled actions without explanation (not capability-driven).
- Error messages that leak sensitive information (internal URLs, raw paths, credentials) or provide no next step.

### Design Inspiration Strategy

**What to Adopt**
- Non-ambiguous state model (GitHub-style): pending/success/fail + next action everywhere.
- Upload UX patterns (Drive/Dropbox): queue/progress + recovery, without losing context.
- Context-preserving navigation (OneDrive): breadcrumbs + coherent return behavior.

**What to Adapt**
- “Reliability state language” (Dropbox) into a web explorer context: explicit status without overpromising sync semantics.
- Share-link page clarity (OneDrive/Drive) while respecting Drive’s capability model and MountProvider-specific semantics.

**What to Avoid**
- Any infinite spinner pattern; any action without an explanatory state.
- Any operator/support output that is not no-leak or that prescribes a single proxy implementation.

## Design System Foundation

### 1.1 Design System Choice

We will **keep and extend the existing project design system** (existing UI kit + existing tokens + existing UI patterns).  
We will **not introduce a new third-party design system** (e.g., Material/Ant/etc.) for v1.

### Rationale for Selection

- **Strict visual alignment with the current UI**: no visual refresh in v1; only additive components within the current look and feel.
- **Speed and consistency**: reusing existing components and patterns minimizes UX/QA risk and reduces implementation time.
- **Reduced divergence**: avoids parallel component libraries and inconsistent interaction patterns.
- **Accessibility baseline continuity**: keeps the current a11y posture (WCAG 2.1 AA “no regressions”) and focuses improvements on critical flows.

### Implementation Approach

- **Reuse-first**: default to existing UI kit components and established patterns.
- **No new component library adoption (even partial)** unless explicitly approved in the PRD.
- **Targeted extension only (10–25%)**: introduce new components only when existing ones cannot express required UX states cleanly.
  - Examples of justified new components:
    - **Operator Diagnostics UI**: health status cards/badges, `failure_class` display, safe evidence blocks.
    - **State/Banner components**: “Feature not enabled”, “still working” (time-bounded loading), actionable error states.
    - **Mount/Admin components**: secret reference field (never the secret), validate/refresh actions, last refresh timestamps.
- **Consistency rules**:
  - Prefer extending existing UI kit components before creating new ones.
  - New components must use existing tokens and follow existing spacing/typography patterns.
  - New interaction states must remain capability-driven and avoid dead/disabled actions without explanation.

### Customization Strategy

- **No brand refresh**: maintain strict alignment with the current visual system.
- **Token-bounded customization**: any styling adjustments happen through existing tokens/themes, not ad-hoc styling.
- **Component governance**: when adding a new component, define its purpose (which UX state it covers), variants, and accessibility expectations to prevent drift.

## 2. Core User Experience

### 2.1 Defining Experience

Drive’s defining experience is **context-preserving file work in a web explorer**:

“I find the right file/folder → I act on it (upload/preview/share/WOPI) → I return to the exact same context (same folder, same selection, same view).”

This combines two equally critical pillars:
- **Upload that just works** (reliable, explicit progress, recoverable failures).
- **Find/act without losing context** (actions never disorient; the explorer remains the user’s anchor).

### 2.2 User Mental Model

Primary user mental model: **a Google Drive / OneDrive-like web drive**, backed by a workspace concept.

Potential surprise/friction points (must be made explicit in UX):
- **Workspace vs folder**: where am I? what scope am I acting in? who can see what?
- **Permissions + link reach (public/restricted)**: what sharing mode is active, and what it implies.
- **Capability-driven preview/WOPI**: preview/WOPI is not always available. Availability depends on file type, permissions, and whether WOPI is enabled and healthy for the current backend. The UI must explain availability and avoid dead actions.
- **SMB Mount (MountProvider) as gateway**: no sync semantics; out-of-band renames/moves can break a mount link target and must be communicated cleanly.

### 2.3 Success Criteria

The core experience is successful when:
- After an upload completes, the file appears in the current folder **without manual refresh**, and the user remains in the same context (folder/selection/view).
- Upload progress is visible (queue/progress), and completion is explicit.
- If an upload fails, the error is actionable (retry/next step) and does not leak sensitive info.
- For eligible files, preview/WOPI either works, or shows a clear state + next action (no infinite loading).
- For mount share links: `404` = invalid/unknown token; `410` = valid token but target missing due to out-of-band change.

### 2.4 Novel UX Patterns

This experience uses **established patterns** (web explorer, modals, toasts, side panels) with a strict “twist” that differentiates self-host Drive:

- **Context-preserving by default** (anchored navigation and return behavior).
- **Capability-driven UX** (availability is explicit; no dead actions; guidance when disabled).
- **No-leak by design** (user-facing messages + operator-facing outputs never expose sensitive details).
- **Operator-diagnosable trust**: when issues are caused by environment/edge/storage, diagnostics surface the right audience model (INTERNAL/PROXY vs EXTERNAL/BROWSER) with safe evidence and next actions.

No novel interaction metaphors are required; the innovation is in **reliability, clarity of state, and diagnosability**, not in new UI patterns.

### 2.5 Experience Mechanics

**Defining flow: Upload within the Explorer (context-preserving)**

1) Initiation
- User is in a specific folder context (workspace + folder).
- User drops files or clicks upload.

2) Interaction
- A visible queue appears with per-file progress, and the queue/progress remains visible even if the user navigates to another folder, so users can keep working without losing upload status.
- User stays in the explorer context; navigation remains possible without losing the ongoing upload’s status.

3) Feedback
- Clear success/failure per file.
- Failures include a next action (retry / guidance) and never leak sensitive info.
- Loading states are time-bounded: if an operation exceeds a threshold, the UI transitions to “still working / retry / contact admin” instead of spinning indefinitely.

4) Completion
- New items appear in the list.
- Context is preserved (folder + selection + view; scroll position when feasible).
- Next actions (preview/share/WOPI) are offered only if available (capability-driven); otherwise, the UI explains why and what to do next.

## Visual Design Foundation

### Color System

- **Brand guidelines:** follow the existing project branding and tokens strictly; no new palette or visual refresh in v1.
- **Semantic colors:** use existing semantic mappings (primary/secondary/success/warning/error/info) as provided by the current tokens/UI kit.
- **Token-bounded colors only:** do not introduce ad-hoc hex colors; use tokens only to preserve contrast guarantees.
- **States & messaging:** error/warning/success/disabled states must remain consistent with existing patterns; avoid introducing new “color meanings”.
  - Long-running operations must be time-bounded and degrade into an explicit “still working / retry / contact admin” state (no indefinite spinners).

### Typography System

- **Typography is fixed for v1:** no global font or hierarchy changes.
- Only **local adjustments** are allowed when strictly necessary, and only via existing components (e.g., using existing variants/sizes), not by introducing a new typographic scale.

### Spacing & Layout Foundation

- **Explorer density:** keep the Explorer experience dense/efficient (desktop-first). No spacing refresh in v1.
- **New surfaces:** Operator Diagnostics / admin-like panels may use a more balanced spacing locally for readability, but must stay within existing layout patterns and tokens.
- Prefer existing layout primitives/patterns (existing UI kit layouts, panels, modals) before creating new ones.

### Accessibility Considerations

- **WCAG 2.1 AA contrast everywhere** (baseline, “no regressions”).
- **Focus visibility & consistency:** focus must be clearly visible and consistent, especially in modals and dropdown menus.
- **Keyboard navigation:** ensure practical keyboard navigation through tree + list (tab/arrow behavior) with correct focus management.
- **Toasts / upload feedback:** status updates must be announced properly (aria-live) **without stealing focus**.

## Design Direction Decision

### Design Directions Explored

We explored multiple directions within strict constraints (existing tokens/UI kit/patterns; no visual refresh):
- Explorer-centric baseline (dense, desktop-first).
- Operator diagnostics placement: non-invasive right panel vs dedicated route.
- State-first patterns: “still working / retry / contact admin”, “feature not enabled”, actionable errors (no-leak).
- Preview/WOPI clarity: eligible files + enabled/healthy + explicit states.
- Mount secrets UX: secret ref only + validate/refresh + no-leak.
- Diagnostics cards/badges and runbook-oriented guidance (proxy-agnostic edge contracts).

### Chosen Direction

**v1 Hybrid (suite-ready): D1 + D2 + D4 + D5 + D6**
- **D1** Explorer baseline as the core product surface (lowest divergence risk).
- **D2** Diagnostics in the Explorer right panel (v1) for non-invasive operator UX.
- **D4** State-first banners and strict state rules (trust/clarity; no infinite loading; actionable; no-leak).
- **D5** Preview/WOPI clarity (eligible files; integration enabled/healthy; explicit states; no indefinite spinners).
- **D6** Mount secrets UX (secret reference only; validate/refresh; status and timestamps; never reveal secrets).

### Design Rationale

- **Minimize product/QA surface area in v1**: avoid introducing a new Settings/Admin area inside Drive.
- **Trust-first UX**: explicit states, time-bounded long-running operations, actionable errors, and no-leak messaging.
- **Explorer mental model alignment**: diagnostics and guidance remain close to where users operate (context-preserving).
- **Suite integration readiness**: Drive should integrate into a broader “Control Panel” ecosystem without rework.

### Implementation Approach

**Diagnostics v1 (right panel) = two levels**
- **Quick health**: a compact summary reflecting both INTERNAL/PROXY and EXTERNAL/BROWSER audiences (e.g., per-audience status + top `failure_class` + `next_action_hint`).
- Optional actions (capability-driven):
  - “Export support bundle” (no-leak)
  - “Open in Control Panel” (future integration)

**Suite-ready invariants (no rework path)**
- Diagnostics are **API-first**: Drive exposes stable endpoints consumable by an external UI (health/diagnostics/support bundle).
- Diagnostics endpoints return safe evidence only (no-leak).
- Shared model: structured statuses including INTERNAL/PROXY vs EXTERNAL/BROWSER audiences, `failure_class`, safe evidence (no-leak), and `next_action_hint`.
- The Drive right-panel diagnostics UI is a **renderer** of these APIs (portable component), not a bespoke logic embedded in the panel.

**State banners rules**
- No permanent banners; only contextual/time-bounded.
- Every message is no-leak and includes a next action (“retry / download / contact admin / link runbook”).

**Mount secrets UI**
- Secret field = reference + status only (“configured/invalid/last refresh/last success”).
- Actions: “Validate connection” + “Refresh/Re-check”; never display the secret.

## User Journey Flows

### Journey J2 — End User (S3): upload → preview → share → WOPI (eligible + enabled/healthy)

Goal: Upload and act on files without losing context.  
Key constraints: S3 upload is browser presigned; long-running operations are time-bounded; no-leak; capability-driven; upload queue/progress remains visible cross-folder.

```mermaid
flowchart TD
  A[User in Explorer<br/>Context = workspace + folder + selection + view] --> B{Start upload}
  B -->|Drag & drop| C[Client validates files<br/>(type/size/permissions)]
  B -->|Click Upload| C

  C --> D{can_upload entitlement?}
  D -->|No| E[Show no-leak error<br/>+ next action (request access/contact admin)] --> A
  D -->|Yes| F[Create/Update upload queue (visible cross-folder)]

  F --> G[For each file:<br/>Request presigned URL (EXTERNAL/BROWSER)]
  G --> H[Browser uploads to S3 via presigned request<br/>Progress updates per file]
  H --> I{Upload completed?}
  I -->|No| K[Show actionable failure<br/>(retry / check network / contact admin)<br/>No-leak] --> F
  I -->|Yes| J[Notify backend upload-ended<br/>Update list in current folder]

  J --> L[File appears without manual refresh<br/>Context preserved (folder/selection/view; scroll when feasible)]
  L --> M{User selects file action}

  M -->|Preview| N{Eligible file + permission?}
  N -->|No| O[Explain why + next action<br/>(download / request permission / doc)] --> L
  N -->|Yes| P[Open preview]
  P --> Q{Loading exceeds threshold?}
  Q -->|No| R[Preview shown] --> L
  Q -->|Yes| S[Still working state<br/>retry / download / contact admin<br/>No infinite loading] --> L

  M -->|Share| T[Open share modal/page<br/>Modes + permissions explicit] --> L

  M -->|WOPI| U{Eligible file + permission + WOPI enabled & healthy}
  U -->|No| V[Explain unavailable + next action<br/>(runbook / download)] --> L
  U -->|Yes| W[Launch WOPI]
  W --> X{Loading exceeds threshold?}
  X -->|No| Y[WOPI opened] --> L
  X -->|Yes| Z[Still working state<br/>retry / contact admin<br/>No infinite loading] --> L
```

### Journey J3 — End User (SMB mount via MountProvider): browse → upload → preview → share → WOPI + out-of-band path changes

Goal: Use SMB as a gateway inside the same Explorer mental model.  
Key constraints: Mount is a "workspace/root" in the tree; SMB is backend-mediated streaming (not sync); share links are path-based; out-of-band rename/move can break targets; share link semantics must distinguish 404 vs 410 for MountProvider.  
Note: `mount.upload` / `mount.preview` / `mount.wopi` are MountProvider capability flags to be implemented (future), used here to keep flows capability-driven.

```mermaid
flowchart TD
  A[User in Explorer tree] --> B{Select location}
  B -->|S3 workspace| C[Standard explorer context]
  B -->|SMB mount root (MountProvider)| D[Mount explorer context<br/>(gateway, no sync semantics)]

  D --> E{User action}

  E -->|Browse| F[List directories/files via backend] --> D

  E -->|Upload| G{can_upload entitlement AND mount.upload?}
  G -->|No| H[No-leak error + next action] --> D
  G -->|Yes| I[Create upload queue/toast<br/>Visible cross-folder navigation]
  I --> J[Backend-mediated streaming upload to SMB<br/>Per-file progress if available]
  J --> K{Completed?}
  K -->|Yes| L[Item appears without manual refresh<br/>Context preserved] --> D
  K -->|No| M[Actionable failure (retry/next step)<br/>No-leak] --> I

  E -->|Preview| N{Eligible file + permission AND mount.preview?}
  N -->|No| O[Explain + next action (download)] --> D
  N -->|Yes| P[Preview via backend gateway]
  P --> Q{Loading exceeds threshold?}
  Q -->|No| R[Preview shown] --> D
  Q -->|Yes| S[Still working state<br/>retry / download / contact admin<br/>No infinite loading] --> D

  E -->|Share link| T[Create/Copy MountProvider share link] --> U[Open share link]
  U --> V{Token valid?}
  V -->|No (404)| W[Show Invalid link (404)<br/>No-leak + next action] --> END1[End]
  V -->|Yes| X{Target exists?}
  X -->|Yes| Y[Open file page/preview<br/>States explicit] --> END2[End]
  X -->|No (410)| Z[Show Valid link but target missing (410)<br/>Moved/deleted out-of-band<br/>Explain + next action] --> END3[End]

  E -->|WOPI| AA{Eligible file + permission + WOPI enabled & healthy AND mount.wopi?}
  AA -->|No| AB[Explain + next action (runbook / download)] --> D
  AA -->|Yes| AC[Launch WOPI]
  AC --> AD{Loading exceeds threshold?}
  AD -->|No| AE[WOPI opened] --> D
  AD -->|Yes| AF[Still working state<br/>retry / contact admin<br/>No infinite loading] --> D
```

### Journey J5 — Support / Operator: incident → classify → audience-aware diagnostics → support bundle (no-leak)

Goal: Diagnose failures without SSH and without leaks; make INTERNAL vs EXTERNAL breakpoints immediately visible.  
Key constraints: Diagnostics are API-first; payload is shared with external Control Panel UI; endpoints return safe evidence only (no-leak); quick health reflects both audiences explicitly; actions are capability-driven and may be 0/1/2 visible.  
Both actions may be visible at the same time.

```mermaid
flowchart TD
  A[Incident reported<br/>(upload/preview/WOPI/share failing)] --> B[Operator opens Diagnostics (right panel v1)]
  B --> C[Fetch diagnostics payload (API-first)<br/>Safe evidence only (no-leak)]
  C --> D[Render Quick Health<br/>INTERNAL/PROXY + EXTERNAL/BROWSER<br/>Overall = worst-of (optional)]

  D --> E{Which audience failing?}
  E -->|INTERNAL/PROXY| F[Show failure_class + safe evidence<br/>(request_id/status/hashes)<br/>+ next_action_hint]
  E -->|EXTERNAL/BROWSER| G[Show failure_class + safe evidence<br/>+ next_action_hint]
  E -->|Both| H[Keep both visible<br/>Prioritize worst-of first]

  F --> I[Proxy-agnostic guidance<br/>(edge contracts, not one proxy)]
  G --> I
  H --> I

  I --> J{Need escalation?}
  J -->|No| K[Apply fix / config change] --> L[Re-run quick diagnostics] --> D
  J -->|Yes| M[Determine available actions<br/>(capability-driven, 0/1/2 visible)]

  M --> N{Any actions enabled?}
  N -->|No| R[Feature not enabled + runbook link] --> K
  N -->|Yes| S[Show enabled actions (may be 1 or 2)]

  S -->|Export bundle enabled| O[Generate/Download support bundle<br/>No-leak] --> K
  S -->|Open in Control Panel enabled| Q[Open external Control Panel UI<br/>Same payload/model] --> K
```

### Journey Patterns

- Context-preserving by default: return to the same folder/selection/view (scroll when feasible) after actions.
- State clarity everywhere: success/failure are explicit; long-running ops are time-bounded (no indefinite spinners).
- Capability-driven UI: no dead actions; always explain “why unavailable” + next action.
- No-leak posture: UI + diagnostics endpoints + bundles expose safe evidence only (no raw paths/keys/credentials).
- Audience-aware diagnostics: INTERNAL/PROXY vs EXTERNAL/BROWSER are always visible as distinct statuses.

### Flow Optimization Principles

- Minimize steps to value (upload/preview/share) while keeping trust-building feedback visible.
- Prefer non-invasive surfaces (modals/right panel) for v1 to reduce routing/QA risk.
- Keep work unblocked: upload queue/progress remains visible cross-folder navigation.
- Make every failure actionable (retry / download / contact admin / runbook link), never ambiguous.

## Component Strategy

### Design System Components

**Policy / constraints**
- Reuse the existing UI kit, tokens, and patterns already used in Drive.
- No new component library adoption (even partial) unless explicitly approved in the PRD.
- Prefer extending existing UI kit components before creating new ones.
- Do not introduce ad-hoc hex colors; use tokens only to preserve contrast guarantees.

**Core primitives (already available)**
- Buttons, inputs, tooltips, dropdown menus
- Modals/dialogs
- Icons + spinners/loaders
- Layout primitives (header, main layout, responsive helpers)
- Toast container pattern (already present)

**Local building blocks (already in Drive)**
- `Toaster` / `ToasterItem` and `addToast` for non-blocking feedback
- `InfoRow` for label/value rows in panels
- Upload feedback UI via `FileUploadToast` (per-file progress)
- Explorer right panel shell (existing pattern to extend for Diagnostics)

### Custom Components (v1 scope guard)

To stay within the “10–25% custom” budget, v1 only introduces the strictly necessary custom components. Everything else is implemented as composition/patterns using existing UI kit primitives, until standardization pressure justifies a dedicated component.

#### DiagnosticsPanel (Right Panel Renderer)

**Purpose:** Provide operator-grade, no-leak diagnostics inside the existing Explorer right panel (v1 non-invasive surface).  
**Usage:** When “Diagnostics” is enabled; otherwise show `FeatureNotEnabledState`.  
**Anatomy:** Title + audience statuses + key failure highlights + safe evidence + action area.  
**States:** loading, success, partial-fail (one audience failing), fail (both), feature-disabled.  
**Accessibility:** status conveyed via text (not color-only); keyboard reachable actions; no focus traps; `aria-live` only for meaningful refresh events (rate-limited).  
**Content Guidelines:** safe evidence only (e.g., request_id/status/hashes), never raw internal URLs/paths/keys/credentials.  
**Interaction Behavior:** “Re-run quick diagnostics” refreshes the same view; actions are capability-driven (no dead buttons).

#### AudienceHealthStatusPair

**Purpose:** Make INTERNAL/PROXY vs EXTERNAL/BROWSER breakpoints immediately visible (side-by-side).  
**Usage:** Always in Diagnostics quick health (worst-of overall optional).  
**States:** ok / degraded / failing (with `failure_class`).  
**Accessibility:** explicit labels per audience; consistent reading order.

#### StateBanner (Time-bounded)

**Purpose:** Trust/clarity surface for context-specific warnings/errors without permanent clutter.  
**Usage:** Contextual only; never permanent.  
**States:** info/warn/error; dismissible when appropriate; auto-expire when resolved.  
**Accessibility:** does not steal focus; announced when it appears (use `aria-live` carefully to avoid spam).

#### FeatureNotEnabledState

**Purpose:** Capability-driven UX: explain unavailable features instead of dead/greyed actions.  
**Usage:** Diagnostics actions (export bundle, open control panel), mount features not enabled.  
**Content:** short explanation + runbook link + “contact admin”.

#### SecretRefField (Mount Secrets)

**Purpose:** Configure mount credentials without ever revealing the secret.  
**Usage:** Mount connection “Secrets” section (SMB first; generic MountProvider later).  
**Anatomy:** secret ref input (path/name), status, timestamps (last refresh / last success).  
**Actions:** Validate connection, Refresh/Re-check (capability-driven).  
**States:** not configured, configured, invalid ref, validation failed (no-leak error + next action), ok.  
**Accessibility:** form labels, error association, keyboard support.

#### ValidationResultPanel (Mount Connection)

**Purpose:** Display “status + failure_class + safe evidence + next_action_hint” for validate/refresh outcomes.  
**Usage:** After validate/refresh actions in Mount secrets flow.  
**No-leak:** strict safe evidence only.

### Component Implementation Strategy

**Surface constraint (v1)**
- No new Settings/Admin area in v1; operator surfaces attach to existing Explorer patterns (right panel / modals).

**Reuse-first approach**
- Composition-first: build new surfaces by composing existing UI kit primitives + tokens.
- Prefer reusing existing building blocks (e.g., `InfoRow`, Explorer right panel shell, `Toaster`/`ToasterItem`) before introducing new helpers.

**API-first diagnostics (no rework path)**
- API-first Diagnostics: `DiagnosticsPanel` renders the exact same payload shape the external Control Panel would consume (no parallel logic).
- No-leak by design: diagnostics endpoints (and any exported artifacts/bundles) return safe evidence only (no raw internal URLs/paths/keys/credentials).
- Safe evidence is an allow-list (explicit allow-list), not “remove sensitive fields”.

**Time-bounded long-running states (preview/WOPI)**
- UX rule (not a technical wrapper): if an operation exceeds a threshold, the UI replaces indefinite loading with an explicit “still working” state offering actions (retry / download / contact admin / runbook link). No infinite spinners.
- Integration constraint: standardize states within existing preview/WOPI surfaces (reuse current loading/error patterns); do not introduce a parallel state system.

**A11y and announcements**
- `aria-live` announcements must be rate-limited and meaningful (avoid announcing every progress tick).
- Prefer announcing milestones: “upload started”, “upload failed”, “upload completed”, plus actionable error summaries.

**`failure_class` display rule**
- `failure_class` is an identifier/code (readable + copyable), not a severity.
- Severity comes from status (ok/degraded/failing) and audience (INTERNAL/PROXY vs EXTERNAL/BROWSER).

### Implementation Roadmap

**Phase 1 (v1 must-have; aligns with D1+D2+D4+D5+D6)**
- `DiagnosticsPanel` + `AudienceHealthStatusPair`
- `StateBanner` + `FeatureNotEnabledState`
- Time-bounded long-running state pattern (preview/WOPI)
- `SecretRefField` + `ValidationResultPanel`
- Minimal “safe evidence + next action” rendering pattern (composition/shared patterns; promote to components only if duplication appears)

**Phase 2 (v1 completion / hardening)**
- Standardize “safe evidence + next action” as dedicated components if duplication appears
- Diagnostics capability-driven actions surfaces (export bundle / open control panel)
- MountProvider share-link error state patterns (404 vs 410) when those routes are implemented

**Phase 3 (post-v1 polish)**
- A11y refinements (consistent focus management in modals; improved announcements for upload/diagnostics refresh)
- Density tuning for diagnostics surfaces (within tokens; no Explorer visual refresh)

## UX Consistency Patterns

### Button Hierarchy

**When to Use**
- Use existing UI kit button variants only; do not introduce new button styles.
- In any surface, expose at most one “primary” action (if any). Prefer secondary/tertiary for everything else.

**Visual Design**
- Primary: “commit” actions only (e.g., Save, Confirm, Upload).
- Secondary: common actions (e.g., Retry, Download).
- Tertiary: utility actions (e.g., Close, Copy, Expand/Collapse, Open details).

**Behavior**
- Capability-driven:
  - Hide actions by default when unavailable.
  - Show as disabled only when it helps the user understand why it’s unavailable (discoverability), and always with “why + next action”.
  - Never show disabled actions without an explanation.
- Destructive actions require confirmation (modal) and never run silently.
- For operator actions (Export bundle / Open in Control Panel), both actions may be visible at the same time (capability-driven).

**Accessibility**
- Buttons must be keyboard reachable; visible focus; do not steal focus on state changes.

**Mobile Considerations**
- Keep the same hierarchy; avoid adding extra steps. Ensure tap targets remain usable (no regressions).

### Feedback Patterns

**When to Use**
- Toasts: transient, non-blocking feedback (e.g., “copied”, “restore complete”, non-critical errors).
- Banners: contextual, time-bounded states that impact the current context (e.g., degraded preview/WOPI, feature not enabled).
- Inline errors: form validation and field-level issues.
- Modals: confirmations and high-impact user decisions.

**Behavior**
- Every failure is actionable: always provide a next action (retry / download / contact admin / runbook link).
- No-leak messaging: UI never displays raw internal URLs/paths/keys/credentials.
- Do not show raw error objects or stack traces anywhere in the UI.
- Announcements: `aria-live` must be meaningful and rate-limited (avoid announcing every progress tick). Prefer milestones: “upload started / upload failed / upload completed”.

**No infinite loading rule**
- Long-running operations are time-bounded: after a threshold, replace indefinite loading with an explicit “still working” state (retry / download / contact admin / runbook link).
- The “still working” state must appear without losing context (same panel/modal/surface) and propose non-destructive actions.

### Form Patterns

**Validation**
- Inline validation on blur and/or submit; show a clear error message and next action.
- Avoid exposing sensitive technical details; errors should be user/operator actionable.

**Secrets / Mount credentials**
- Secret value is never displayed; the secret reference (path/name/ref) may be displayed.
- Secret values are write-only (never readable back) if an admin UI exists.
- Status is explicit: not configured / configured / invalid ref / last refresh / last success.
- Validate and Refresh/Re-check actions are capability-driven; results show status + `failure_class` + safe evidence (no-leak) + next action.

### Navigation Patterns

**Context-preserving default**
- After actions (upload/rename/share/WOPI/preview exit), return to the same folder/selection/view; preserve scroll position when feasible.
- Upload progress must remain visible even if the user navigates across folders (cross-folder continuity).
- Back/forward browser navigation must remain coherent with breadcrumbs.

**Surfaces (v1 non-invasive)**
- No new Settings/Admin area in v1; operator/support surfaces attach to existing Explorer patterns (right panel / modals).

**Mounts in the Explorer mental model**
- Mounts appear as a root/workspace in the tree (gateway semantics; no sync).
- Explain out-of-band behavior where it matters (e.g., share link target can disappear if moved/deleted outside Drive).

### Modal and Overlay Patterns

**Behavior**
- Consistent close mechanics (ESC + close button).
- Clear titles, explicit outcomes, and explicit error states (no ambiguous “something went wrong”).

**Accessibility**
- Focus management: focus enters the modal, remains trapped, returns to the launcher on close.
- Do not steal focus for toasts or passive status updates.

### Empty, Loading, and Error States

**Empty states**
- Empty selection, empty folder, no results: explain what it means and what to do next (create/upload/search).

**Loading states**
- Use a consistent loading presentation and messaging; for long-running operations, apply the time-bounded rule (“still working” state).

**Error states**
- No-leak posture: show safe evidence only (allow-list), plus `failure_class` as a copyable identifier.
- Severity is derived from status (ok/degraded/failing) and audience; `failure_class` is not a severity.
- Prefer “copy individual values” for safe evidence (avoid encouraging bulk copy of long evidence).

### Additional Patterns

**Diagnostics (audience-aware)**
- Always show INTERNAL/PROXY and EXTERNAL/BROWSER statuses explicitly (side-by-side); “overall” may be derived as worst-of, but must not hide per-audience truth.
- Diagnostics UI must render the exact same payload shape as the external Control Panel would consume (no parallel logic).
- Diagnostics endpoints and exported artifacts return safe evidence only (allow-list), not “remove sensitive fields”.
- Guidance is proxy-agnostic: describe required edge contracts, not a specific reverse proxy implementation.

**Sharing links (MountProvider)**
- For MountProvider share links, UX distinguishes:
  - 404: invalid token
  - 410: valid token but target missing (moved/deleted out-of-band)
- Copy should be clean and no-leak; always provide a next action.

## Responsive Design & Accessibility

### Responsive Strategy

**Overall posture**
- Desktop-first (primary use). Keep Explorer efficient/dense.
- Responsive “no regressions”: mobile/tablet remain usable for basic actions; no “mobile app” promise in v1.

**Desktop**
- Default layout: Explorer mental model with high information density.
- Right panel is the primary non-invasive surface for contextual info (incl. v1 Diagnostics).

**Tablet**
- Avoid introducing new navigation paradigms; preserve the Explorer mental model.
- Use existing responsive modes (as defined by the UI kit) to collapse secondary surfaces when space is constrained.
- Prefer keeping the Explorer core loop intact; panels (right panel / auxiliary content) may become overlays or collapsible sections rather than introducing new routes.

**Mobile**
- Guarantee at least:
  - Open a share link and view the file (or see a clear error state)
  - Download a file / open via system viewer
- Upload on mobile: best-effort / no regressions (not a v1 guarantee).
- Keep interactions simple: single-column priority, avoid multi-pane dependencies.

**Cross-device invariants**
- Context-preserving: after actions, return to the same folder/selection/view; preserve scroll position when feasible.
- Upload progress continuity: upload queue/progress remains visible even if the user navigates across folders (within feasible UX constraints per device). On mobile, this may be implemented as a persistent toast or a dedicated upload screen rather than multi-pane UI.

### Breakpoint Strategy

- Use the existing breakpoints and responsive helpers provided by the current UI kit/design system (no custom breakpoint definitions unless required).
- Treat “tablet mode” as the same condition used in the codebase (e.g., UI kit `useResponsive()`), to avoid design/implementation drift.

### Accessibility Strategy

**Compliance target**
- Baseline: WCAG 2.1 AA “no regressions”.

**Targeted v1 improvements (2–3 visible)**
- Explorer tree/list keyboard navigation + focus management (tab/arrow patterns as applicable).
- Modals (share/WOPI/confirmations): focus management, ARIA labels/roles, and predictable close behavior.
- Upload feedback: accessible progress/errors; announcements without stealing focus.

**Core rules**
- Visible focus indicator everywhere (including menus/modals).
- Do not rely on color only to convey status; always provide text labels (especially in Diagnostics statuses).
- Long-running operations are time-bounded: no indefinite spinners; degrade to “still working / retry / contact admin / runbook link” without losing context.
- Announcements: `aria-live` must be meaningful and rate-limited (avoid announcing every progress tick). Prefer milestones (started/failed/completed).
- No-leak: never expose raw internal URLs/paths/keys/credentials; do not show raw error objects or stack traces.

### Testing Strategy

**Responsive**
- Validate core flows on desktop/tablet/mobile sizes using the same responsive modes as implementation.
- Manual sanity on real devices for share-link open + download/open viewer.

**Accessibility**
- Automated checks (e.g., axe) on critical routes and modals (Explorer, `/explorer/items/files/[id]` share-link file page, preview/WOPI surfaces, Diagnostics panel).
- Run axe as smoke-level gating: “no regressions” vs baseline + realistic thresholds (not necessarily 0 violations everywhere on v1).
- Manual keyboard-only pass on Explorer + modals (focus order, traps, return-to-launcher).
- Screen reader spot checks on critical flows (upload feedback, diagnostics refresh, error states).

### Implementation Guidelines

**Responsive implementation**
- Reuse existing layout patterns (Explorer shell, right panel, modals) rather than introducing new Settings/Admin areas in v1.
- Use existing tokens; do not introduce ad-hoc hex colors.

**A11y implementation**
- Prefer semantic HTML; ARIA only when necessary and correct.
- Ensure modals trap focus and restore focus to launcher on close.
- Rate-limit announcements; avoid noisy updates for progress.
- Make “still working” states explicit and actionable; never leave users in ambiguous loading.
