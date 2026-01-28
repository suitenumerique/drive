## 1. Responsive Width

- [ ] 1.1 Add container ref and ResizeObserver to measure container width in PreviewPdf.tsx
- [ ] 1.2 Calculate dynamic page width: use container width (minus padding) when < 768px, otherwise 800px
- [ ] 1.3 Pass dynamic width to react-pdf's Page component instead of fixed BASE_WIDTH
- [ ] 1.4 Adjust zoom calculations to work with dynamic base width

## 2. Touch Gesture Handling

- [ ] 2.1 Add touch event state (tracking touches, initial distance, initial zoom)
- [ ] 2.2 Implement pinch distance calculation helper function
- [ ] 2.3 Add touchstart handler to capture initial two-finger positions
- [ ] 2.4 Add touchmove handler to calculate zoom delta from pinch gesture
- [ ] 2.5 Add touchend handler to clean up touch tracking state
- [ ] 2.6 Ensure pinch zoom respects MIN_ZOOM and MAX_ZOOM bounds

## 3. Pan When Zoomed

- [ ] 3.1 Add pan offset state (x, y translation)
- [ ] 3.2 Implement single-finger drag detection (when zoomed > 1x)
- [ ] 3.3 Calculate pan bounds based on zoom level and container size
- [ ] 3.4 Apply pan offset to page wrapper transform
- [ ] 3.5 Reset pan offset when zoom returns to 1x or page changes

## 4. CSS Touch Control

- [ ] 4.1 Add touch-action: none to PDF container during active gesture
- [ ] 4.2 Use touch-action: pan-y when at fit-to-width zoom (allow page scroll)
- [ ] 4.3 Prevent default on touch events only when handling pinch/pan gestures

## 5. Testing

- [ ] 5.1 Test responsive width on mobile viewport sizes (320px, 375px, 428px)
- [ ] 5.2 Test pinch-to-zoom gesture on touch device/emulator
- [ ] 5.3 Test pan gesture when zoomed in
- [ ] 5.4 Test that desktop behavior is unchanged (800px width, button zoom)
- [ ] 5.5 Test device rotation triggers width recalculation
