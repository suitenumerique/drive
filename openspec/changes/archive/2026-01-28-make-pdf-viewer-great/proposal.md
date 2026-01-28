## Why

The current PDF viewer (`PreviewPdf`) is a minimal implementation that renders all pages at once without navigation or zoom controls. It uses placeholder classnames ("Example") that don't follow the app's BEM conventions, and the content is left-aligned instead of centered. Users need standard PDF viewing controls to navigate multi-page documents efficiently.

## What Changes

- Add page navigation controls (previous/next page buttons)
- Add page jump input (direct navigation to specific page with current/total display)
- Add zoom controls (zoom in, zoom out, percentage display, reset)
- Center the PDF content in the viewport
- Refactor classnames to follow BEM convention (`.pdf-preview`, `.pdf-preview__controls`, etc.)
- Render pages on-demand instead of all at once for better performance

## Capabilities

### New Capabilities

- `pdf-viewer-controls`: Navigation toolbar with page controls (prev/next, page jump) and zoom controls (in/out, percentage, reset) following existing patterns from ImageViewer and VideoPlayer

### Modified Capabilities

None - this is an enhancement to an existing component without spec-level requirement changes.

## Impact

- **Code**: `src/frontend/apps/drive/src/features/ui/preview/pdf-preview/PreviewPdf.tsx` and `pdf-preview.scss`
- **Dependencies**: No new dependencies (uses existing `react-pdf`, `@gouvfr-lasuite/ui-kit`, `@openfun/cunningham-react`)
- **Patterns**: Will reuse zoom control pattern from ImageViewer and control layout from PreviewControls
