## Context

The PDF viewer component (`PreviewPdf.tsx`) uses `react-pdf` to render PDFs. Currently it renders pages at a fixed 800px width with CSS transform-based zoom. On mobile devices (320-428px viewports), this causes horizontal overflow and poor UX.

Current implementation:
- Fixed `BASE_WIDTH = 800` passed to react-pdf's `<Page>` component
- Zoom via CSS `transform: scale(zoom)` on wrapper div
- No touch event handling for gestures
- Controls already have basic mobile styles but no touch interaction

## Goals / Non-Goals

**Goals:**
- PDF fits within mobile viewport on initial load (no horizontal overflow)
- Users can pinch-to-zoom on touch devices
- Users can pan the PDF when zoomed in beyond viewport
- Maintain existing desktop experience (800px base width, button controls)

**Non-Goals:**
- Continuous scroll (multiple pages visible) - keep single-page rendering
- Double-tap to zoom - only pinch gesture
- Swipe to change pages - keep button navigation
- Offline PDF caching

## Decisions

### Decision 1: Dynamic width based on container size

**Choice**: Use `useRef` + `ResizeObserver` to measure container width, pass dynamic width to react-pdf's `<Page>` component.

**Rationale**: react-pdf's `<Page>` accepts a `width` prop that controls actual render resolution. Using this instead of CSS transforms gives better text clarity and proper hit areas for links/annotations.

**Alternatives considered**:
- CSS `max-width: 100%` on canvas - Blurry text, doesn't affect actual render
- CSS transforms only - Already in use, causes overflow issues

### Decision 2: Native touch events for pinch-to-zoom

**Choice**: Implement pinch-to-zoom using native `touchstart`, `touchmove`, `touchend` events with distance calculation between two touch points.

**Rationale**: Avoids adding a dependency. The gesture is straightforward (track two fingers, calculate distance delta, map to zoom).

**Alternatives considered**:
- `@use-gesture/react` library - Adds ~15KB, overkill for single gesture
- `hammerjs` - Larger footprint, designed for complex gesture apps

### Decision 3: CSS touch-action for pan control

**Choice**: Use `touch-action: none` on the PDF container when handling gestures, allowing JavaScript full control. When not zoomed, use `touch-action: pan-y` to allow vertical page scroll.

**Rationale**: Prevents browser's native pinch-zoom (which zooms entire page) while allowing controlled behavior.

### Decision 4: Breakpoint for mobile detection

**Choice**: Use 768px breakpoint (matching existing SCSS) and container width measurement. If container width < 768px, use container width as PDF width. Otherwise, use 800px.

**Rationale**: Consistent with existing mobile breakpoint in `PreviewPdf.scss`. Container measurement handles cases where PDF is in a narrow panel on desktop.

## Risks / Trade-offs

**[Risk] Touch event conflicts with scroll** → Use `touch-action` CSS property to explicitly control which gestures browser handles vs JavaScript handles. Only intercept two-finger gestures.

**[Risk] Performance on low-end mobile devices** → react-pdf already handles canvas rendering efficiently. Keep zoom bounds (50%-200%) to prevent excessive re-renders.

**[Risk] Zoom + pan state complexity** → Keep zoom state unified between button and touch zoom. Pan offset resets when zoom returns to 1x or when page changes.

**[Trade-off] No gesture library = manual event math** → Acceptable for single gesture. If more gestures needed later, reconsider adding `@use-gesture/react`.
