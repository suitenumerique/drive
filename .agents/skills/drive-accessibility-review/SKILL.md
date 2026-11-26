---
name: drive-accessibility-review
description: Review the accessibility of added or modified frontend code in La Suite Drive (PRs, diffs, React components, styles, explorer features). Covers HTML semantics, accessible names, ARIA, keyboard navigation, focus entry and restoration (Cancel, Escape, submit, removed trigger), screen-reader announcements, forms, dialogs, menus, the file grid, the tree, drag and drop and the file preview. Verifies in a real browser by default (loads the browser tools and starts the stack when needed) and keeps static, browser, axe and screen-reader evidence apart.
---

# Drive accessibility review

Review the changed experience end to end. Report evidenced regressions, not a generic checklist. Stay in review mode unless the user asked for fixes.

## 1. Scope

- Read the diff the user asked for. For a branch, compare against the merge base with the real target branch (`git merge-base`), not only the last commit. Include uncommitted changes when asked. Never reset, stash or stage user work.
- Map changed files to the rendered components, routes and shared primitives, and to their other consumers: a change in `features/ui/components/` or in a shared explorer component affects every caller, the SDK pages (`pages/sdk/`) included. Include styles, portals, event handlers and async state. Backend-only changes are in scope only if they change what the UI renders (abilities, error responses).
- Before reviewing, write a small matrix: **flow/state | expected focus | expected accessible information or announcement | how it was verified**. Cover the states that apply: idle, open, loading, success, empty, error, cancel, trigger removed.
- Target WCAG 2.2 A/AA. APG is pattern guidance, not a normative requirement: do not report an APG deviation as a WCAG failure. Do not claim RGAA or legal conformance.

## 2. Drive landmarks

App: `src/frontend/apps/drive/src` (`@/` alias). Read the implementation of a primitive before reporting that it lacks semantics or focus handling: wrappers often delegate them. Conversely, using an accessible primitive does not make its usage accessible.

- **UI primitives:** `@gouvfr-lasuite/ui-components` (`Modal`, `DropdownMenu`, `ContextMenu`, `Tooltip`, `Button`, `Icon`…), read in `node_modules/@gouvfr-lasuite/ui-components`. A few components use `react-aria-components` directly (the explorer filters).
- **File grid:** `features/explorer/components/embedded-explorer/` is a `<table>` built with TanStack Table. Its keyboard navigation and selection live in `hooks/useTableKeyboardNavigation.ts`, which also moves focus to the table on load and when the selection changes: check that a change there does not steal focus from a dialog, a menu or an input.
- **Pointer-only interactions:** the marquee selection (`@viselect/react`) and drag and drop (`Draggable.tsx`, `Droppable.tsx`, `ExplorerDndProvider.tsx`, the tree). Each needs a keyboard path to the same result: the keyboard selection of the grid, the Move dialog (`components/modals/move/`).
- **Tree:** `features/explorer/components/tree/`.
- **Dialogs:** `features/explorer/components/modals/` (create, rename, move, share, search, confirmations). Some set their initial focus by hand (`ExplorerRenameItemModal.tsx`, `ExplorerSearchModal.tsx`).
- **Focus restoration and announcements:** the app has no shared helper for either. Do not cite one, and do not add one by reflex: check first what the primitive already does (focus return of `Modal` and `DropdownMenu`).
- **Toasts:** `addToast` and `ToasterItem` (`features/ui/components/toaster/`, on `react-toastify`). Check in the browser whether a toast is announced: a visible toast is not proof.
- **Preview and editors:** `features/ui/preview/CustomFilesPreview.tsx`, and the WOPI editor in an iframe (`features/wopi/WopiEditorFrame.tsx`): the inside of the iframe belongs to Collabora or OnlyOffice and is out of scope, its title and the way in and out are not.
- **i18n:** accessible names go through `t("some.key")`, with the key added to every language of `features/i18n/translations.json`.

Search with the Grep tool (`rg` may not be installed in the shell), then narrow the search to the affected feature: `aria-|tabIndex|autoFocus|onKeyDown|\.focus\(|role=`.

## 3. Review the changed flows

Check only the dimensions the change touches:

1. **Semantics and names:** native elements over `div` plus ARIA, meaningful accessible names and labels, heading order and landmarks, valid ARIA relationships (`aria-controls`, `aria-describedby` targets exist), current state (`aria-expanded`, `aria-selected`, `aria-current`, `aria-pressed`, `aria-sort` on sortable columns). Icon-only buttons need a name. Do not duplicate the visible text in `aria-label` with different wording.
2. **Keyboard:** every action reachable and operable with the keyboard, the expected keys for the widget (arrows in menus, trees and grids; Escape closes), no trap, focus indicator visible (WCAG 2.4.7) and focused elements not entirely hidden by a sticky header or overlay (WCAG 2.4.11).
3. **Focus lifecycle:** where focus lands on open, then after each exit path separately: Cancel, Escape, close button, outside click, success, failure, deletion, navigation, unmount. Focus returns to the trigger when appropriate, or to a logical, visible, enabled successor when the trigger is gone or the context has changed (deleted or moved item, folder left). Check nested overlays (a menu opened from a row, a confirmation over a dialog).
4. **Announcements:** state changes the user cannot see without moving focus (upload progress and end, delete, restore, copy link, number of search results, errors) must be communicated to screen readers, either through existing accessible information or an announcement when needed. Avoid duplicate announcements and races against focus moves.
5. **Forms:** labels, required fields and error messages programmatically associated with their input (create, rename, share).
6. **Visual and pointer:** contrast of new colours (use Cunningham tokens), zoom to 200 % and reflow at 320 px, content shown on hover also shown on focus and dismissible, target size (2.5.8), an alternative to dragging (2.5.7), `prefers-reduced-motion`.

Describe the expected behaviour before choosing a fix. Do not add ARIA, a focus trap or a live region by reflex.

## 4. Verify in a real browser (default, not optional)

Source reading alone misses most accessibility regressions (focus that lands nowhere, a name that differs from the code, a sticky header hiding the focus). Run the changed flows in a browser unless it is truly impossible, and make the attempt before saying it is.

1. **Get a browser tool.** Tools may be deferred: search for them (`ToolSearch` with `playwright`, `chrome-devtools`, `chrome`, `browser`) and load their schemas before concluding there is none. Playwright MCP and Chrome DevTools MCP are the usual ones; Claude in Chrome and the built-in browser also work (load their skill first). Discover the real tool names; never invent them. No browser MCP is configured in the repository itself.
2. **Get the stack running.** Check `http://localhost:3000` and the backend on :8071. A failed request is not a reason to stop: load the `drive-start` Skill and start what is missing (it runs only the needed Makefile targets, and copes with a local `yarn dev`). Check that the served build contains the reviewed change (branch checked out, `yarn dev` or the frontend container).
3. **Log in and prepare data.** Seeded accounts of `docker/auth/realm.json`: `drive` / `drive`, or `user-e2e-chromium` / `password-e2e-chromium`; do not guess others. Work in a disposable folder and delete it afterwards.
4. **Drive each row of the matrix with real key presses** (`Tab`, `Shift+Tab`, `Enter`, `Space`, arrows, `Escape`), not clicks or `.focus()`. After every transition read the accessibility snapshot and `document.activeElement`, and take a screenshot for focus visibility and for a focus hidden under a sticky header. Check each exit path of an overlay separately. Repeat with a pointer when behaviour should differ between keyboard and pointer.
5. **Also exercise** 200 % zoom and a 320 px viewport (resize), and `prefers-reduced-motion` (emulate it).
6. **axe** is **not** a dependency of the E2E suite. Use it only through the available tooling (an MCP, or injecting it through DevTools); do not add the package without asking. Scan every rendered state, portals included.
7. **Only if it is really impossible** (no browser tool after searching, the stack cannot start after trying), finish the source review, say which step failed and why, and list the exact remaining manual steps. Never report a blocked check as passing, never skip the browser because a first request failed, and never install tools or change MCP configuration silently.
8. An accessibility tree or a clean axe run is not speech. Only an actual screen-reader session (NVDA, VoiceOver, …) verifies what is spoken and when.

A finding raised from the source and not reproduced in the browser stays **static** and is reported as a risk, not as a confirmed issue. A browser run that contradicts the source reading wins.

Label every piece of evidence: **static**, **browser/DOM**, **axe**, **screen reader**, or **not verified**.

## 5. Tests

- Do not write E2E tests unless the user explicitly asks; when they do, follow the `drive-e2e-test` skill (Chromium only, focused spec, existing helpers). In review mode, describe the smallest meaningful test instead.
- The Jest tests of the app run without a DOM: a focus or name regression can only be covered by an E2E test.
- In focus assertions, do not let the test fix the focus: no click or `.focus()` between the action under test and `toBeFocused()`. Use `page.keyboard` (Tab, Shift+Tab, Enter, Escape) for the measured interaction: a click does not prove keyboard reachability.
- Prefer `getByRole` / `getByLabel`; a test ID may locate a container but does not check the accessible name. No arbitrary waits, no `force: true` clicks.

## 6. Report

Lead with confirmed findings in order of impact. For each:

- **Severity / confidence**, `file:line`, flow and state.
- **User impact**: the concrete key sequence that fails.
- **Observed vs expected**, evidence label, WCAG criterion when the mapping is clear.
- **Smallest fix**, reusing a local primitive, and the regression check.

Severity by user impact: **critical**: an essential flow cannot be completed and there is no alternative; **high**: a major navigation or operation barrier; **medium**: confusing or recoverable; **low**: minor friction.

Keep apart new regressions (checked against the base when possible, otherwise say it is unknown), pre-existing issues nearby (search the issues labelled `accessibility` before reporting one as new), and unverified risks. Merge findings caused by the same shared primitive.

End with a compact coverage table (flow/state × static / browser / axe / screen reader) stating which browser tool and stack were used, or the step that failed, and the manual checks still needed. Say "No confirmed issue found in the reviewed scope" when that is the case, never "fully accessible" or a conformance percentage. Name the dimensions and tools that were skipped or failed.
