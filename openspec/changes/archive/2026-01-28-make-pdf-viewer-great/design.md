## Context

The current `PreviewPdf` component (`src/frontend/apps/drive/src/features/ui/preview/pdf-preview/PreviewPdf.tsx`) uses `react-pdf` to render PDFs but has several limitations:
- Renders all pages at once (performance issue for large documents)
- No navigation controls (prev/next, page jump)
- No zoom controls
- Uses placeholder classnames ("Example") instead of BEM conventions
- Content is left-aligned instead of centered

The app has established patterns in `ImageViewer` for zoom controls and in `VideoPlayer` for navigation that should be reused.

## Goals / Non-Goals

**Goals:**
- Single-page rendering with navigation controls (prev/next buttons, page number input)
- Zoom controls following the existing `ZoomControl` pattern from `ImageViewer`
- Centered PDF content in the viewport
- BEM classnames consistent with other preview components (`.pdf-preview`, `.pdf-preview__controls`, etc.)

**Non-Goals:**
- Drag/pan functionality (unlike ImageViewer, PDFs scroll naturally)
- Touch pinch-to-zoom (can be added later)
- Thumbnail sidebar navigation
- Text search within PDF
- Annotation support

## Decisions

### 1. Single-page rendering vs all pages

**Decision:** Render only the current page, not all pages at once.

**Rationale:** The current implementation renders all pages simultaneously, which causes performance issues for large documents. Rendering a single page and providing navigation controls is the standard PDF viewer pattern and significantly reduces memory usage.

**Alternative considered:** Virtualized list of pages - more complex, not needed for MVP.

### 2. Reuse ZoomControl component from ImageViewer

**Decision:** Extract and reuse the existing `ZoomControl` component.

**Rationale:** `ImageViewer` already has a well-designed zoom control with the correct styling and behavior. Reusing it ensures consistency and reduces code duplication. The component is already exported and can be imported directly.

**Alternative considered:** Create PDF-specific zoom control - rejected as it would duplicate existing code.

### 3. Page navigation control layout

**Decision:** Place page navigation (prev/next, current/total) in a control bar below the PDF, alongside zoom controls.

**Rationale:** Follows the pattern established by `VideoPlayer` which has controls below the content. Keeps the PDF area clean and focused on the document.

**Layout:**
```
[Prev] [Page X of Y] [Next]  |  [Zoom-] [100%] [Zoom+]
```

**Alternative considered:** Floating controls overlay - rejected as it obscures content.

### 4. Page input behavior

**Decision:** Use a text input for page number that:
- Shows current page number
- Allows direct typing to jump to a page
- Validates input (clamps to valid range 1-numPages)
- Updates on blur or Enter key

**Rationale:** Standard PDF viewer behavior users expect.

### 5. Zoom behavior

**Decision:** Zoom affects the `width` prop of react-pdf's `Page` component.

**Rationale:** react-pdf's `Page` component accepts a `width` prop that controls rendering size. Zoom will be implemented as a multiplier on a base width (e.g., `baseWidth * zoom`). This is simpler than CSS transforms and works well with react-pdf's rendering.

**Zoom range:** 0.5x to 2x (50% to 200%), step 0.25, default 1x (100%)

### 6. Centering approach

**Decision:** Use flexbox centering on the container.

**Rationale:** Simple CSS solution. The PDF container will use `display: flex; justify-content: center; align-items: flex-start;` to center horizontally while allowing vertical scroll.

## Risks / Trade-offs

**[Single page view limits context]** Users can't see multiple pages at once.
→ Mitigation: Clear page indicator (X of Y) and easy navigation. Thumbnail view can be added later.

**[Zoom affects only width]** Height is proportional, may cause layout shifts.
→ Mitigation: Container has fixed height with overflow scroll, so shifts are contained.

**[No keyboard shortcuts initially]** Unlike ImageViewer, not implementing keyboard nav in MVP.
→ Mitigation: Arrow keys for prev/next and +/- for zoom can be added in a follow-up.
