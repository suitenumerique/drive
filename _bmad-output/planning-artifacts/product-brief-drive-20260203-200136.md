---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/brainstorming/brainstorming-session-20260203-110252.md
  - _bmad-output/planning-artifacts/architecture/architecture-kickoff-brief.md
  - _bmad-output/planning-artifacts/handoff/brainstorming-handoff.md
  - _bmad-output/planning-artifacts/packaging/axe-packaging-epics-stories.md
  - _bmad-output/planning-artifacts/sources/agent-playwright-chrome-docker.md
  - _bmad-output/planning-artifacts/sources/SELFHOST_SUITE_NUMERIQUE_REVIEW.md
  - _bmad-output/planning-artifacts/storage/axe-storage-epics-stories.md
  - _bmad-output/planning-artifacts/storage/axe-storage-tests-gates.md
  - _bmad-output/planning-artifacts/storage/filestash-smb-mounts-analysis.md
  - _bmad-output/planning-artifacts/upstream/drive-open-backlog.md
  - _bmad-output/planning-artifacts/upstream/drive-open-issues.json
  - _bmad-output/planning-artifacts/upstream/drive-open-prs.json
  - _bmad-output/planning-artifacts/wopi/axe-wopi-epics-stories.md
  - docs/architecture.md
  - docs/ds_proxy.md
  - docs/entitlements.md
  - docs/env.md
  - docs/installation/kubernetes.md
  - docs/installation/README.md
  - docs/metrics.md
  - docs/release.md
  - docs/resource_server.md
  - docs/setup-find.md
  - docs/theming.md
date: 2026-02-03T20:01:49+00:00
author: Apoze
---

# Product Brief: drive (Apoze/drive fork)

## Executive Summary

`Apoze/drive` is a continuation of Drive (MIT, open source) with a clear goal: make it a complete, production-usable **self-hosted** file service while preserving upstream-like discipline (clean boundaries, tests, CI, conventions) so future upstreaming remains possible (human-driven, optional).

The project focuses on three product pillars:

1) **Self-host packaging & operations**: a supported Docker/K8s trajectory, explicit canonical public URL, TLS strategy, backup/restore and upgrade/rollback runbooks.
2) **Storage correctness across S3-compatible providers**: Drive-integrated **contract tests** for the real Drive ↔ proxy ↔ S3 contract (INTERNAL/PROXY vs EXTERNAL/BROWSER), to support SeaweedFS first and later Ceph RGW, with optional ds-proxy profiles.
3) **Storage extensibility**: a Drive-native, plugin-like **MountProvider** boundary that keeps S3 behavior unchanged while enabling an **SMB mount v1** (list/read → upload/preview → share links + WOPI).

Separately, this project aims to be “agent-operable”: BMAD registry as source of truth, deterministic gates, and reproducible artifacts so a dev agent can implement end-to-end with reliable review loops.

---

## Core Vision

### Problem Statement

Drive is not yet a “complete self-host solution” for many real-world environments:

- production packaging and upgrade paths are incomplete for non-Kubernetes users (official docs emphasize Kubernetes);
- S3-compatible object stores (SeaweedFS, Ceph RGW, proxies) differ subtly (SigV4 host signing, range semantics, copy behavior, special chars), leading to hard-to-debug failures;
- the storage surface is primarily S3-oriented, limiting extension to non-S3 backends such as SMB without a clear boundary.

### Problem Impact

- Self-hosters lose time to brittle deployments, misconfigured proxies, and “works in dev / breaks in prod” issues.
- Provider differences create failures that are costly to triage (missing contract tests and deterministic evidence).
- Adding new storage types risks architectural drift unless a stable boundary exists.

### Why Existing Solutions Fall Short

- Self-host stacks often overfit to one proxy/provider, causing hidden coupling (host mismatch, domain replace logic, headers propagation).
- “S3-compatible” claims are not enough: the product needs **proof** of the specific capabilities Drive relies upon (range, copy metadata replace, encoding).
- Mounting non-S3 storage inside an S3-first app typically becomes a patchwork unless designed around explicit provider boundaries and capability-driven feature activation.

### Proposed Solution

Evolve `Apoze/drive` into a self-host first, correctness-driven Drive by:

- standardizing a packaging baseline (Docker + K8s) with a single canonical public URL, robust TLS and runbooks;
- introducing Drive-integrated S3 contract tests that validate the most failure-prone behaviors and encode evidence safely (no secrets/paths);
- defining a MountProvider boundary (plugin-like) and implementing SMB as a first non-S3 provider, staged to keep S3 behavior unchanged;
- keeping development deterministic and agent-operable (BMAD registry strict mirror to GitHub, gates runner, artifacts, quarantine rules).

### Key Differentiators

- **Contract-first storage support**: “provider compatibility” is enforced via Drive-integrated CTs, not vendor-specific hacks.
- **Explicit audiences** for signing: INTERNAL/PROXY vs EXTERNAL/BROWSER with “signed_host == used_host” invariants.
- **Extensible storage** via MountProvider while preserving the existing S3-first model.
- **Deterministic delivery**: strict mirror registry ↔ GitHub, deterministic gates, and failure-class taxonomy.

---

## Target Users

### Primary Users

1) **Self-host Operator (Admin / Platform Engineer)**
   - Runs Drive in Docker or Kubernetes behind an edge proxy (Nginx baseline).
   - Needs repeatable install, upgrades, backups, and clear failure evidence.
   - Cares about: OIDC integration, storage reliability, observability, incident debugging.

2) **Organization Integrator (SRE / DevOps / Suite Maintainer)**
   - Integrates Drive into a broader suite (IdP, resource server, entitlements, metrics, theming).
   - Needs stable configuration surface, conventions, and CI gates.

3) **End Users (Knowledge Workers)**
   - Upload, preview, share links, and document editing (WOPI/Collabora).
   - Expect “it just works” and consistent behavior across storage backends.

### Secondary Users

- **Security / Compliance**
  - Requires TLS correctness, secrets hygiene, and “no-leak” policies in logs/artefacts.
- **Maintainers / Contributors**
  - Prefer small changes, clear boundaries, and tests that prove behavior (upstreamability as a “light constraint”).

### User Journey

1) **Discovery & Evaluation**
   - Operator reads install docs, validates prerequisites (OIDC, Postgres, Redis, S3).
   - Runs preflight to confirm environment readiness.

2) **Deployment**
   - Installs via Kubernetes (existing baseline) or Docker (target baseline v1 for this fork).
   - Sets canonical public URL, configures TLS, and validates `/media` proxy contract.

3) **Daily Usage**
   - Users upload/download/preview; ops monitors gates/metrics and upgrades.
   - Optional: enable SMB mount(s) for additional legacy storage access.

4) **Value Moment**
   - Storage “just works” across providers; share links and WOPI edits behave predictably.
   - Ops can debug failures via deterministic evidence + failure classes.

---

## Success Metrics

### User / Ops Success Metrics

- **Time-to-first-successful-deploy** (Docker + K8s): operators can reach a working login + file upload within a documented time budget.
- **Upgrade success rate**: upgrades follow a single documented procedure, with a smoke-test gate and rollback path.
- **Storage correctness**: contract tests pass for baseline provider profile(s) (SeaweedFS blocking; others optional).
- **Deterministic evidence**: on failure, reports include `failure_class` + safe evidence (no credentials/paths/keys).

### Business Objectives

- Provide a complete self-host Drive that reduces operational burden and increases confidence in storage/proxy correctness.
- Maintain a low-divergence fork with the option to upstream later (human decision).

### Key Performance Indicators

- **CI green rate** on main branches (core gates) and on storage/auth changes (CT-S3 gates).
- **E2E pass rate** (Chrome-only, host-first) with explicit quarantine rules for flakes.
- **Mean time to diagnose** (MTTD) storage/proxy related incidents reduced via contract tests and failure-class taxonomy.

---

## MVP Scope

### Core Features

**Automation / Delivery (agent-operable)**

- BMAD registry as source of truth; GitHub issues/PRs on `Apoze/drive` are strict mirrors (fingerprint B+).
- Deterministic gates runner (diff → gates selection) with artifacts and no-leak scanning of `_bmad-output/**` text artifacts.

**Self-host packaging baseline**

- Nginx edge baseline (contractual `/media` flow), with Docker and Kubernetes tracks.
- Canonical public URL concept (single source of truth) for redirects/links/CORS/WOPI allowlists (to be implemented as part of packaging scope).
- TLS: dev automation (mkcert) and production options (Ingress+cert-manager or Nginx+ACME).
- Backup/restore and upgrade runbooks (minimum viable).

**Storage correctness**

- Drive-integrated S3 contract tests with audiences INTERNAL/PROXY vs EXTERNAL/BROWSER.
- Provider profiles: SeaweedFS blocking; ds-proxy optional (non-blocking) and future Ceph RGW.

**Storage extensibility**

- MountProvider interface + routing with **no behavior change** to S3 (stage 1).
- SMB provider staged:
  1) list/read
  2) upload/preview
  3) share links + WOPI (capability-driven)

**WOPI/Collabora**

- Per-backend constraints:
  - S3-backed WOPI requires bucket versioning (current codebase dependency).
  - SMB-backed WOPI uses app version string + locks (does not depend on S3 versioning).

### Out of Scope for MVP

- Automatic upstream PR creation or any agent interactions with `suitenumerique/drive` (no read/write).
- Full “sync” between SMB and S3 namespaces; SMB share links are path-based and may break on out-of-band renames (explicitly accepted).
- Multi-browser E2E matrix (Chrome-only for determinism).
- Vendor-specific storage hacks without contract-test proof.

### MVP Success Criteria

- Operators can deploy and operate Drive with a documented, repeatable process and deterministic checks.
- Baseline storage provider profile passes the mandatory Drive-integrated S3 contract suite.
- MountProvider boundary exists and can support SMB v1 staged delivery without refactoring S3 call sites prematurely.

### Future Vision

- Expand provider profiles (Ceph RGW, additional proxies) using declarative profiles + CT evidence.
- Expand MountProvider ecosystem beyond SMB (future storage backends) without architectural drift.
- Harden observability (trace IDs, structured logs) and build optional performance harnesses outside core CI.
