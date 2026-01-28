## Why

The PDF viewer currently renders at a fixed 800px width, causing horizontal overflow on mobile devices where viewports are typically 320-428px wide. Users cannot see the entire PDF on initial load and must scroll horizontally. Additionally, mobile users expect pinch-to-zoom gestures for document viewing, which is not currently supported.

## What Changes

- **Responsive width**: PDF pages will scale to fit the container width on mobile viewports instead of using a fixed 800px width
- **Pinch-to-zoom**: Add touch gesture support for pinch-to-zoom on mobile devices
- **Fit-to-width on load**: Mobile devices will display the PDF fitted to screen width on initial load (100% of viewport width)
- **Touch-friendly controls**: Ensure the control bar remains usable and doesn't overflow on small screens

## Capabilities

### New Capabilities

- `pdf-viewer-touch`: Touch gesture support for the PDF viewer including pinch-to-zoom and pan gestures

### Modified Capabilities

- `pdf-viewer-controls`: Add responsive width behavior and fit-to-width requirements for mobile viewports

## Impact

- **Code**: `PreviewPdf.tsx` - add responsive width calculation and touch gesture handling
- **Styles**: `PreviewPdf.scss` - add responsive breakpoints and touch-action CSS properties
- **Dependencies**: May need a touch gesture library (e.g., `use-gesture`) or native touch event handling
- **Testing**: Requires mobile device/emulator testing for touch gestures
