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
