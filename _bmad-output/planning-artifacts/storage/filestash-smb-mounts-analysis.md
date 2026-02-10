# Filestash vs Drive MountProvider (SMB v1) — Feasibility & Impact Analysis

## Context (Project Constraints)

- Primary repo: `Apoze/drive` (agents must not interact with upstream `suitenumerique/drive`).
- Goal: make Drive a complete self-hostable solution.
- SMB v1 requirements (as stated):
  - second storage space (SMB) visible in Drive UI
  - **not synchronized** with S3
  - v1 includes **upload + preview + share links + WOPI/Collabora**
  - share links may break if SMB paths change outside Drive (accepted)
  - permissions are global per mount (single service account), no per-path RBAC in SMB

## What Filestash Is (Relevant Facts)

- Filestash is a universal data access gateway / file manager supporting many protocols (SMB/S3/WebDAV/…).
- It has a plugin-based architecture; the backend storage interface is implemented in Go (`IBackend` with `Ls/Stat/Cat/Save/Mv/Rm/...`).
- License: **AGPL-3.0**.

## Key Decision Driver

Your SMB v1 feature set is not "just browsing SMB"; it requires Drive to own:

- link sharing (tokens, enforcement, UX)
- WOPI integration (tokens/locks/version string/save)
- audit/no-leak constraints aligned with Drive
- a consistent permission model (global mount permissions)

Therefore the primary question is not "can we access SMB?", but "who is the system-of-record for links/WOPI/security and how do we keep it deterministic for the agent dev?".

## Options

### Option A — Embed Filestash code inside Drive (NOT recommended)

**Feasibility:** technically possible in theory, but practically high-friction.

**Major blocker:** Filestash is **AGPL**. Embedding/linking its code into a MIT codebase is likely to force copyleft obligations on the combined work.

**Conclusion:** do not embed Filestash code into Drive.

### Option B — Run Filestash as a separate service and integrate at UI level (Limited fit)

Example: deploy `filestash` container alongside Drive and expose it via Nginx; integrate via link/iframe/portal.

**Pros**
- fastest path to "SMB browsing" and multi-protocol access
- Filestash already handles many protocols and has a plugin ecosystem

**Cons / mismatches with your v1 requirements**
- Share links would belong to Filestash (or would require custom integration) → breaks "Drive owns links"
- WOPI/Collabora integration would be separate / duplicated
- Auth/SSO and permission model become duplicated (Drive vs Filestash)
- UI/UX and audit/no-leak policies become inconsistent unless heavily customized
- Still must comply with AGPL for Filestash distribution/changes (fine, but operationally notable)

**Conclusion:** good as an *optional external tool*, not as the implementation path for "SMB inside Drive with Drive-native links/WOPI".

### Option C — Implement a Drive-native `MountProvider` interface + SMB provider (Recommended)

Drive remains system-of-record for:
- share links, WOPI, authorization, UX
- logging/no-leak rules

SMB becomes just another backend behind a **stable Drive interface**.

**Pros**
- meets requirements: share links + WOPI integrated in Drive
- "plugin-like" future: add WebDAV/NFS/SharePoint later without refactoring core flows
- upstream-friendly architecture: "capabilities" and provider neutrality
- deterministic gates and contract tests can target Drive endpoints (agent-friendly)

**Cons**
- more engineering than a Filestash iframe
- SMB semantics/perf edge cases must be handled (timeouts, atomic write, large files)

**Implementation notes (suggested)**
- Define `MountProvider` with operations needed by v1:
  - list, stat, read-stream (supports range if possible), write-stream, mkdir, delete, move/rename
- Add a `capabilities` map per provider:
  - `supports_range`, `supports_atomic_rename`, `supports_streaming_upload`, `supports_wopi`
- For SMB in Python:
  - use a maintained SMB client library supporting streaming and random access
  - implement upload as: write temp + fsync/close + rename (best-effort atomic)
  - implement previews via range when possible; otherwise explicit fallback path

**Conclusion:** best match for your v1 requirements and for the BMAD/agent autonomy model.

## Recommended Approach (Product-first, PR-friendly as a constraint)

1) Keep Filestash as a **reference design** (its plugin interface is a useful inspiration), not a dependency.
2) Implement Drive-native `MountProvider` + SMB provider.
3) Treat Filestash as optional "future integration" only if you later want a separate gateway product in the stack.

## Impact Summary

- **Licensing:** Filestash AGPL makes embedding a non-starter; sidecar is acceptable if you comply for that component.
- **Complexity:** sidecar reduces initial SMB effort but increases long-term system complexity (two auth/UX/link models).
- **Determinism:** Drive-native provider architecture is best for strict gates, contract tests, and an agent that can finish the project end-to-end.
