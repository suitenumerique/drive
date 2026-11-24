---
name: drive-pr-review
description: Review pull requests and code changes in La Suite Drive. Use when reviewing a PR, branch, diff, or set of changes in the Drive repository. Focus on correctness, regressions, security, permissions, file upload and download, storage, WOPI, API contracts, database performance, frontend behavior, concurrency, deployment risks, and missing tests. Verifies frontend-side changes in a real browser automatically. Produce a concise review prioritizing actionable issues over style comments.
---

# Drive PR review

Review as a senior engineer who knows the Drive architecture (see `AGENTS.md`).
Find the real problems: bugs, regressions, security holes, data loss,
production performance, deployment failures. One real bug is worth more than
ten speculative comments. Do not modify code unless asked.

## 1. Understand the change

- For a PR, read the title, description, commits and diff
  (`gh pr view <n>`, `gh pr diff <n>`). For a branch, diff against the merge
  base with its target (`git merge-base`), not only the last commit.
- Work out the intent, then which areas it touches: backend, frontend, API
  contract, permissions, storage, WOPI, Celery, deployment, tests.
- Classify the diff. It is **frontend side** as soon as it touches
  `src/frontend/` (`apps/drive`, `packages/sdk`, translations, styles, assets;
  the E2E app on its own does not count), or when a backend change alters
  something the UI displays (abilities, error responses, API fields). That
  triggers the browser check of section 2, automatic when a browser tool is
  available. Backend-only, docs-only and CI-only PRs skip it explicitly.
- Read the surrounding code before reporting: another layer may already
  handle the case. For each guard, flag or sentinel the PR adds or changes,
  find every reader.

## 2. What to check

**Correctness first**: edge cases, null, empty or missing values, error and
fallback paths, partial failures that leave an inconsistent state, retries,
stale state, accidental behaviour changes.

**Permissions.** The backend is the source of truth; the frontend only
follows it.

- Rights come from `Item.get_abilities(user)`, computed by the permissions
  backend (`core/permissions/backends/role.py`) and enforced by
  `core/api/permissions.py`. They combine the accesses of the item and of
  its ancestors (direct or through a team) with the link reach (restricted,
  authenticated, public), the link role, its password and its expiration, also
  inherited, and with folder restrictions. Check every new or changed action
  against an anonymous user, an authenticated user without access, each role,
  each link reach, an item whose ancestor grants more or less, a restricted
  folder, and a deleted item.
- The same viewsets are exposed to other applications by the resource server
  (`core/external_api/`), for the actions listed in the `EXTERNAL_API`
  setting: a change to one of those actions, or to a serializer field,
  changes that API too.
- An ID taken from the request must not reach another user's object; prefer
  filtering the queryset over checking after the fetch. No secret or personal
  data in responses or logs.
- The `e2e` app logs anyone in: any change to `LOAD_E2E_URLS`, to its guard in
  `post_setup` or to `e2e/urls.py` is blocking until proven safe in
  `Production`.

**Files and storage.** User files are untrusted content, served from the
media origin (`MEDIA_BASE_URL`), which a deployment may share with the
application.

- Upload: the browser sends the bytes to S3 (a PUT on the presigned
  `policy`), then calls `upload-ended`, which screens the type (`RESTRICT_UPLOAD_FILE_TYPE`) and
  starts the malware detection. Look for a path that makes a file readable
  before that, or that trusts the name, extension or mimetype sent by the
  client.
- Download and preview: nginx serves the bytes after a subrequest to
  `items/media-auth/`. Look for active content rendered inline (HTML, SVG,
  scripts), a response header relaxed, a file reachable without the
  subrequest, and an S3 key built from user input.
- Quota: check that a path creating bytes (upload, duplication, conversion)
  goes through the entitlements and quota checks (`core/entitlements/`,
  `core/utils/quota.py`).
- Deletion: soft, then hard. A hard delete or a purge that reaches the wrong
  subtree is data loss: read the queryset twice.
- WOPI (`src/backend/wopi/`): the access token gives the editor the rights of
  one user on one file; check its scope, its lifetime and what a lock or a
  save does on a file deleted, moved or changed meanwhile.
- SSRF from user-supplied URLs. Report a security issue only with a plausible
  path, and describe it. If it is exploitable on a released version, tell the
  user privately instead of writing the details in a public review
  (`SECURITY.md`).

**Backend**: N+1 queries or queries in loops (a page lists up to hundreds of
items: anything per item is multiplied), unbounded querysets, a tree lookup
that cannot use an index (see `docs/scaling.md`), a missing index for a new
frequent lookup, related writes outside `transaction.atomic`,
check-then-create races, non-idempotent Celery tasks. Migrations: safe for a
rolling deployment (no long lock or rewrite on the items table, no non-null
column without a default, no code relying on the schema before every instance
has migrated).

**Frontend**: stale state and closures (`react-hooks/exhaustive-deps` is off,
the linter does not catch them), duplicated sources of truth, TanStack Query
keys and invalidation, optimistic updates without rollback, loading, empty,
error and disabled states, rights changing while the page is open, a render
cost multiplied by every row of a large folder
(`docs/architecture/explorer-selection-store.md`), a shared explorer
component changed without checking the SDK pages. Accessibility: use the
`drive-accessibility-review` skill for anything beyond the obvious.

**Runtime check (frontend side PRs).** When your agent exposes a browser tool
(Chrome DevTools or Playwright MCP, ...; never invent tool names), do it
automatically, without being asked, in addition to the source review, never
instead of it. Skip it, and mark the checks **not verified**, when the user
or their own instructions ask for a review by reading the code only. Check
that the dev stack is up, otherwise start it with the
`drive-start` skill; for the stack, login and disposable folder, follow
`drive-accessibility-review` section 4. Then exercise the changed UI: load the
affected pages, snapshot the accessibility tree, try the changed interactions
with the keyboard and the mouse, check a narrow (mobile) width, console errors
and failed network requests, and the error, empty and loading states. Report
browser findings like the others, flagged **verified in browser**; flag the
checks not done **not verified**. If the stack cannot be started, apply the
same marking and state why.

When no browser tool is available, do not install anything or touch any
configuration silently: finish the source review, mark the browser checks
**not verified**, and end the review by telling the user, in these words or
close to them: "You don't have a browser MCP installed (Chrome DevTools or
Playwright), so I could not check this PR in a browser. For a better review,
consider adding one. Do you want me to add it to the project settings of your
agent?" If they accept, add it to the project-level configuration of your
agent (not the global one), then propose a second pass once the agent has
reloaded it, as it may need a restart.

**API contract**: both sides agree on field names, nullability, enums, status
codes and error shape; an old frontend can talk to a new backend during a
deployment; `core/tests/swagger/*.json` regenerated with the change.

**Configuration and deployment**: safe defaults, a disabled feature flag keeps
the old behaviour, Helm values updated, no secret committed.

## 3. Drive conventions

Report these as **Minor** unless they break something:

- `CHANGELOG.md`: an entry under `[Unreleased]`,
  `- <gitmoji>(type) description`, less than 80 characters per line, only
  for a change users or operators can see. An internal refactor or a
  tests-only PR needs none: it takes the `noChangeLog` label, which lifts the
  CI check. An entry for such a PR is to be removed.
- Commits: `<gitmoji>(type) lowercase title` with a body explaining why; no
  `fixup!` commit left.
- User strings go through `_()` (backend) or `t()` with a key (frontend), the
  key present in every language of `translations.json`.
- A new backend setting is documented in `docs/env.md`.
- No item ID, user ID or path in a Prometheus metric label.
- The word print followed by an opening parenthesis appears nowhere in the
  diff, documentation included: the CI greps the whole diff for it. Backend
  tests use the `settings` fixture.
- Test docstrings state the expected behaviour ("X should Y"), as their
  neighbours do, rather than justifying the test.
- Agent docs stay in step: when the PR renames or removes a Makefile target,
  a compose service, an image, an environment variable, a script or a path,
  grep `AGENTS.md`, `.agents/skills/` and the READMEs for it and ask for them
  to be updated in the same PR. A stale command costs every later agent a
  failed run.

## 4. Tests

Look for the missing test that would catch a real regression: new behaviour,
the fixed bug, permissions, failure paths, migrations with logic, API
contracts. Say what it should check. Do not ask for tests for coverage alone,
and do not ask for E2E tests when a unit or backend test suffices.

## 5. Avoid false positives

Before reporting, confirm the path is reachable, that no other layer handles
it, and that it is a bug rather than a design you would have done
differently. No formatting or naming comments unless they create ambiguity,
and no refactor unrelated to the PR.

## 6. Report

Start with a two-line summary of the change, then the findings ordered by
severity:

- **Blocking**: security hole, data loss or corruption, outage, fundamentally
  wrong behaviour.
- **Important**: a concrete bug or regression to fix before merge.
- **Minor**: a real but low-impact issue, or a convention above.

For each finding:

**[severity] Short title**

- Location: `path/to/file.ext:line`
- Problem, and the scenario in which it happens
- Impact
- Suggested fix, in a sentence or two

For a frontend side PR, add a short **Browser verification** part: what was
loaded, what was exercised, and what was not verified (with the reason).

If nothing meaningful is found, say "No blocking or important issue found",
then list what deserves manual verification.
