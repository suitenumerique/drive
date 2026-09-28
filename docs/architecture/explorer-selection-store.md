# Explorer selection — external store pattern

## Context and symptom

In Drive, the user can select multiple files or folders in the explorer either
by clicking them one by one, or by drawing a rubber-band (marquee) rectangle
with the mouse — every item the rectangle covers is added to the selection.

On folders with a handful of items it works fine. But as soon as a folder
holds **~200+ items on the same page**, the marquee drag becomes janky: small
freezes / FPS drops happen every time the mouse enters or leaves an item. The
experience is broken on large folders — precisely the folders where multi
selection matters the most.

### Isolating the culprit

A simple experiment: replacing every cell body with a plain `<div>hello</div>`
makes the lag **disappear completely**. Conclusion: the cost is **not** in
updating the selection state itself, but in the **render cost of the heavy
cells** (icons, tooltips, dnd-kit `<Draggable>` / `<Droppable>`, etc.) which
were all re-rendered on every mouse tick.

## Diagnosis — where did the render storm come from?

Before this refactor, the selection state lived in a `useState<Item[]>` on the
`GlobalExplorerContext` provider. Any change called `setSelectedItems`, which
triggered the following chain on **every mousemove** that touched an item:

1. **`AppExplorerInner.onSelectionMove`** — the viselect callback fires on
   every mousemove and calls `setSelectedItems(prev => [...])`.
2. **`GlobalExplorerContext`** — new state → new provider value → every
   consumer of `useGlobalExplorer()` re-renders (there are many across the
   tree).
3. **`EmbeddedExplorerGrid`** — recomputes a local `selectedItemsMap` via
   `useMemo` that depends on the new array reference → new map.
4. **`contextValue` of the grid** — `useMemo(..., [props, ...])` where `props`
   is a brand new object on every parent render, so this `useMemo` was
   effectively useless — it produced a new value every time.
5. **`<tbody>`** — the 200+ rows were mapped **inline** without `React.memo`,
   so a parent re-render meant 200 `<tr>` re-renders.
6. **Cells** (`NameCell`, `ActionsCell`, `MobileCell`) — consumed
   `selectedItemsMap` via `useEmbeddedExplorerGridContext()`. No memoization.
   All 200+ cells re-rendered **even when their own `isSelected` had not
   changed**.
7. **Heavy subtrees inside cells** — `<Draggable>` (dnd-kit), `<Tooltip>`,
   `<ItemIcon>`, `<Icon>`, `<LoadingRing>`, `<Droppable>` — all re-rendered on
   every tick for 200 rows.

In other words: a mousemove that only covered **3 new items** still forced
**200 full re-renders** of heavy cells, not 3.

An existing comment in `EmbeddedExplorerGrid.tsx` already admitted the
problem:

> The context is only here to avoid the rerendering of react table cells
> when passing props to cells, with a context we avoid that by passing props
> via context, but it's quite overkill, unfortunately we did not find a
> better solution.

Routing through a React Context does **not** solve the problem — every
consumer of a Context re-renders as soon as its value changes.

## Chosen strategy

**Goal:** during a marquee drag, only the cells whose `isSelected` actually
flipped should re-render. Everything else (parent `EmbeddedExplorerGrid`, the
197 unaffected rows, components higher up in the tree) must stay inert.

**Approach:** replace the React `selectedItems: Item[]` state with a small
**external store**, compatible with React 18's `useSyncExternalStore`, that
exposes **per-id selector hooks**. React bails out automatically when the
snapshot returned by `getSnapshot` is equal (by `Object.is`) to the previous
value → a component subscribed via `useIsItemSelected(id)` only re-renders
when its boolean actually flips from `false → true` or `true → false`.

No new dependency: no Zustand or similar — a tiny store class plus
`useSyncExternalStore` is enough (~150 lines).

### Why `useSyncExternalStore` and not something else?

This is the core of the refactor: it is what makes the **per-id bailout**
possible. Alternatives we considered:

#### Alternative 1 — `useState` + React Context

That was exactly what we had before. Structural issue: **a React Context
notifies all of its consumers whenever its value changes**, with no way to
filter by consumer. You cannot tell a row "only re-render when YOUR id flips",
because React has no visibility into what each consumer actually looks at.
Cannot scale to 200+ rows without tree-wide re-renders.

#### Alternative 2 — `useState` + prop-drilling with `React.memo`

Pass `isSelected: boolean` as a prop to each memoized row. Works in theory,
but in practice:

- The parent (`EmbeddedExplorerGrid`) has to subscribe to the full
  `selectedItems` array to know what to pass to each row → it re-renders on
  every marquee tick.
- Even if `React.memo` bails each row, **the parent still runs the body of
  `.map()` 200 times and creates 200 fresh prop objects**. Cheaper than
  re-rendering 200 subtrees, but still wasteful.
- That parent re-render cascades to everything non-memoized in its subtree
  (contextValue, internal `useMemo`s, etc.).

#### Alternative 3 — Custom event emitter + local `useState` per row

Each row subscribes via `useEffect` to an event emitter and keeps its own
`useState<boolean>` for `isSelected`. Works, but:

- That is **exactly** what `useSyncExternalStore` does internally, only with
  proper SSR support (`getServerSnapshot`), concurrent-mode consistency
  (tearing under Concurrent Mode), and unmount cleanup.
- With a `useEffect` + `useState` roll-your-own, there is a small lag between
  the change and the row render (the effect only runs after commit), which
  can cause visual tearing under rapid updates.
- `useSyncExternalStore` guarantees **synchronous consistency**: the row
  always sees the current store value, never a stale one.

#### What `useSyncExternalStore` does in practice

Its signature is:

```ts
useSyncExternalStore<T>(
  subscribe: (onStoreChange: () => void) => () => void,
  getSnapshot: () => T,
  getServerSnapshot?: () => T,
): T
```

Three functions, React handles the rest:

1. **Calls `subscribe`** once on mount, keeps the teardown for unmount. We are
   handed a callback (`onStoreChange`) that we invoke whenever we want
   subscribers to re-check the snapshot.
2. **Calls `getSnapshot` on every render** and **every time `onStoreChange`
   fires**. It compares the new value to the previous one **with `Object.is`**.
   If they are equal, React **bails out** the component render — the
   function body does not even run.
3. Guarantees consistency: if the value changes mid-render, React re-runs the
   render with the fresh value (no tearing under Concurrent Mode).

That `Object.is` on the snapshot is what makes this design work. For
`useIsItemSelected(id)`, `getSnapshot` returns a **primitive boolean**. Two
equal booleans are `Object.is`-equal → React bails **automatically**, with no
`React.memo`, no custom comparator, no gymnastics.

#### The detail that makes it all work: per-id listeners

`useSyncExternalStore` alone would not be enough if we notified **every**
listener on every change. Imagine: add an item to the selection, notify all
rows → each row re-computes its snapshot → React compares, bails for 199
rows, re-renders 1. That is better than the old situation (no tree-wide
re-render), but every tick still fires 200 `getSnapshot` calls.

`SelectionStore.setSelectedItems` goes further: it diffs **the previous and
new id Maps** (`changedIds`) and only notifies the listeners of ids whose
status actually changed:

```ts
const changedIds = new Set<string>();
prevMap.forEach((_, id) => {
  if (!nextMap.has(id)) changedIds.add(id);
});
nextMap.forEach((_, id) => {
  if (!prevMap.has(id)) changedIds.add(id);
});

changedIds.forEach((id) => {
  this.idListeners.get(id)?.forEach((l) => l());
});
```

Result: if 2 items are added to the selection during a tick, we notify
**exactly 2 listeners**, not 200. React re-renders those 2 rows, and does
literally **nothing** for the other 198 — no render, no `getSnapshot`, not
even an `Object.is`. Optimal.

If the caller passes a new array reference whose id-set is identical to the
previous one (e.g. shift-click over a range that is already fully selected),
the store keeps the previous reference and no listener is woken up at all.

#### One-sentence summary

`useSyncExternalStore` is the only React primitive that simultaneously
(a) subscribes to state living **outside** React, (b) gives **automatic
bailout** when the scoped value does not change, and (c) guarantees
**synchronous, tearing-free rendering** — exactly the three properties needed
so that a marquee tick only re-renders the affected rows.

## Implementation details

### 1. The selection store

File: `src/frontend/apps/drive/src/features/explorer/stores/selectionStore.ts`

Contains:

- A `SelectionStore` class:
  - Internal state: an `Item[]` (stable snapshot for consumers of the full
    list) and a `Map<string, Item>` (O(1) id lookup).
  - Two listener sets:
    - **Global listeners** for components that show the full list or the
      count (selection bar, SDK picker selection bar, drag overlay, etc.).
    - **Per-id listeners** for grid rows that only care about their own
      `isSelected` status.
  - `setSelectedItems(action)` accepts either an array or an updater (same
    signature as `Dispatch<SetStateAction<Item[]>>`). **Only notifies per-id
    listeners whose status actually changed** — the key point that lets the
    197 unaffected rows do nothing.
  - `getSelectedItems()`, `isSelected(id)`, `clear()`, `subscribe()`,
    `subscribeToId()`.
- A `SelectionStoreContext` React context to carry the instance.
- Ergonomic hooks:
  - `useSelectionStore()` — returns the instance (for imperative reads inside
    event handlers).
  - `useSelectedItems()` — full list, global subscription.
  - `useIsItemSelected(id)` — boolean scoped to one id, per-id subscription.
    **This is the hook rows and cells use.**
  - `useHasSelection()` — `count > 0` boolean, useful to show/hide the
    selection bar without subscribing to the full count.
  - `useSelectionCount()` — selection size.
  - `useSetSelectedItems()` — stable setter.
  - `useCreateSelectionStore()` — creates a local instance via `useRef`
    (needed to scope a selection to a subtree, see below).

### 2. Wiring into `GlobalExplorerContext`

File: `src/frontend/apps/drive/src/features/explorer/components/GlobalExplorerContext.tsx`

- The provider creates a `SelectionStore` instance via
  `useCreateSelectionStore()` and exposes it through
  `<SelectionStoreContext.Provider>`.
- `selectedItems`, `selectedItemsMap` and `setSelectedItems` are **removed**
  from `GlobalExplorerContext`'s value. Consumers that needed them now go
  through `useSelectedItems()` / `useIsItemSelected()` /
  `useSetSelectedItems()`.
- Effects that used to clear the selection (right-panel open, folder
  navigation) now call `selectionStore.clear()`.

### 3. Two selection scopes: global and local

The explorer runs in two modes:

- **App mode** — main Drive navigation, one global store created by
  `GlobalExplorerProvider`.
- **Embedded mode** — used by the "Move to" modal (the user picks a target
  folder) and by the SDK picker. Each usage has **its own local selection** —
  selecting a folder in the move modal must not alter the main explorer's
  selection.

Solution: `EmbeddedExplorer` (and its `useEmbeddedExplorer` hook) creates its
own `SelectionStore` via `useCreateSelectionStore()` and exposes it through a
local `SelectionStoreContext.Provider`. Because React providers shadow each
other naturally, grid cells always read the nearest provider's store without
needing to know where the grid is rendered.

### 4. `EmbeddedExplorerGrid` refactor

File: `src/frontend/apps/drive/src/features/explorer/components/embedded-explorer/EmbeddedExplorerGrid.tsx`

- Removed the `selectedItems` / `setSelectedItems` props (the grid reads
  everything through `useSelectionStore()` internally).
- Removed the local `selectedItemsMap` that was recomputed every render.
- Removed `selectedItemsMap` from `EmbeddedExplorerGridContextType`.
- Click / context-menu / over handlers are extracted into stable
  `useCallback`s. Selection reads are **imperative** through
  `selectionStore.getSelectedItems()` or `selectionStore.isSelected(id)` —
  no subscription, no parent re-render during a marquee.
- The `<tbody>` mapping now delegates to a new memoized
  **`EmbeddedExplorerGridRow`** component.

### 5. `EmbeddedExplorerGridRow` component

File: `src/frontend/apps/drive/src/features/explorer/components/embedded-explorer/EmbeddedExplorerGridRow.tsx`

- Wrapped in `React.memo`.
- Reads `isSelected` via `useIsItemSelected(row.original.id)` → subscription
  scoped to this item's id.
- Receives `row`, `isOvered`, `onClickRow`, `onContextMenuRow`, `onOver` as
  props. These props are stable (the row is stable as long as its data does
  not change, the callbacks are `useCallback`s with primitive deps in the
  parent).
- Result: when the selection changes, **only the rows whose status flips
  receive a notification and re-render**. The others bail out at the hook
  level, before the component body even runs.

### 6. Cell memoization

Files:

- `EmbeddedExplorerGridNameCell.tsx`
- `EmbeddedExplorerGridActionsCell.tsx`
- `EmbeddedExplorerGridMobileCell.tsx`

Each cell is wrapped in `React.memo`. `EmbeddedExplorerGridNameCell` (and the
`useDisableDragGridItem` helper in `hooks.tsx`) no longer read
`selectedItemsMap` from the grid context — they use
`useIsItemSelected(item.id)`. They only re-render when their own selection
flips.

### 7. Avoiding cascading re-renders from higher components

The classic trap: if a component high up in the tree (e.g.
`AppExplorerInner`, `ExplorerDndProvider`) subscribes to the full selection
via `useSelectedItems()`, **it** re-renders on every marquee tick, and that
re-render cascades down to `EmbeddedExplorerGrid` → rows → cells. All the
downstream memoization work is wasted.

To avoid that, parents do **not** subscribe to the full list when they don't
need it:

- **`AppExplorerInner`** no longer reads `selectedItems`. To decide between
  the selection bar and the filters it uses `useHasSelection()`, which only
  re-renders when the boolean **flips** (count 0 → 1 or 1 → 0). During a
  marquee, the boolean flips at most twice — imperceptible.
- **`ExplorerDndProvider`** no longer renders the count directly. The drag
  overlay and the move confirmation modal are extracted into two small child
  components (`SelectionCountDragOverlay` and
  `ExplorerTreeMoveConfirmationModalWithCount`) that subscribe to the count
  via `useSelectionCount()`. The provider itself subscribes to nothing, so
  its children do not re-render because of it.
- **`useTableKeyboardNavigation`** — the effect that re-focuses the table
  after each selection change used `[selectedItems]` as a dependency. It now
  uses a **direct imperative subscription** to `selectionStore.subscribe()`
  inside a `useEffect`: the side effect fires, but the host component (the
  grid) is not invalidated.

### 8. Call-site migration

Every file that used to read `useGlobalExplorer().selectedItems` or
`.selectedItemsMap` has been migrated:

- `AppExplorerInner.tsx`
- `AppExplorerGrid.tsx`
- `ExplorerSelectionBar.tsx`
- `ExplorerDndProvider.tsx`
- `ExplorerRightPanelContent.tsx`
- `ExplorerRenameItemModal.tsx`
- `ExplorerMoveFolderModal.tsx`
- `EmbeddedExplorerGridNameCell.tsx` + `hooks.tsx`
- `useTableKeyboardNavigation.ts`
- `EmbeddedExplorer.tsx` + `useEmbeddedExplorer`
- `pages/explorer/trash/index.tsx`
- `pages/sdk/explorer/index.tsx` + `SdkPickerFooter`

Depending on their needs, those files use either `useSelectedItems()`
(reactive list), `useSelectionStore().getSelectedItems()` (imperative read
inside a handler), or `useIsItemSelected(id)` / `useHasSelection()` /
`useSelectionCount()` when a scoped subscription is enough.

## What this refactor solves

### The reported bug

Marquee drag over a folder with 200+ items is smooth again: stable 60 FPS, no
perceivable micro-freeze. On every mouse tick during the marquee:

|                                                  | Before          | After                                                            |
| ------------------------------------------------ | --------------- | ---------------------------------------------------------------- |
| Parent grid renders                              | 1               | **0**                                                            |
| `<tr>` renders                                   | 200             | **= number of rows whose `isSelected` flips** (typically 0–3)    |
| Heavy cell renders (NameCell, etc.)              | 200 × 3 columns | **= number of affected rows × 3**                                |
| Re-renders of Draggable / Tooltip / ItemIcon     | 600+            | **≈ 0–9**                                                        |

### Positive side effects

- **Single click / Cmd+click / Shift+click**: same gains — no more cascading
  re-renders, only the rows that flipped update.
- **Keyboard navigation** (up/down arrows): the table focus effect is now
  decoupled from the render → more efficient, and more correct (no React
  dependency on an always-new array reference).
- **Modals** that consume the selection (rename, move): imperative reads from
  the store, no more superfluous subscriptions.
- **Cleaner code**: gone is the duplicated `selectedItemsMap` (once in
  `GlobalExplorerContext`, once in `EmbeddedExplorerGrid`); gone is the
  comment acknowledging the "Context as a workaround" trick that did not
  actually work.
- **Clean scoping** of local vs global selection: the "Move to" modal and the
  SDK picker now have a strictly isolated selection, with no risk of leaking
  into the main explorer.

### What was left untouched

- `overedItemIds` (the ids of items hovered during a dnd-kit drag) suffers
  structurally from the same problem: it is a `Record<string, boolean>`
  stored in a Context; every update creates a new object and invalidates all
  consumers. During a DnD drag over a large folder, the same cascading
  re-render pattern happens. This refactor does **not** tackle that: it is
  not the reported bug, and the fix is the exact same pattern (external store
  + `useIsItemOvered(id)` hook). To be done in a follow-up if the need
  arises.
