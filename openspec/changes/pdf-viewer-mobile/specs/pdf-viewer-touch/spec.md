## ADDED Requirements

### Requirement: Pinch-to-zoom gesture
The PDF viewer SHALL support pinch-to-zoom gestures on touch devices, allowing users to zoom in and out by placing two fingers on the screen and moving them apart or together.

#### Scenario: Zoom in with pinch gesture
- **WHEN** user places two fingers on the PDF and moves them apart
- **THEN** the PDF zoom level increases proportionally to the finger distance change

#### Scenario: Zoom out with pinch gesture
- **WHEN** user places two fingers on the PDF and moves them together
- **THEN** the PDF zoom level decreases proportionally to the finger distance change

#### Scenario: Pinch zoom respects bounds
- **WHEN** user attempts to pinch-zoom beyond the minimum (50%) or maximum (200%) bounds
- **THEN** the zoom level stops at the boundary

#### Scenario: Pinch zoom updates zoom indicator
- **WHEN** user changes zoom level via pinch gesture
- **THEN** the zoom percentage indicator in the controls updates to reflect the new level

### Requirement: Pan gesture when zoomed
The PDF viewer SHALL allow users to pan the PDF content when zoomed in beyond the viewport boundaries.

#### Scenario: Pan zoomed content
- **WHEN** the PDF is zoomed in such that content extends beyond viewport AND user drags with one finger
- **THEN** the visible portion of the PDF pans in the direction of the drag

#### Scenario: Pan bounds limiting
- **WHEN** user attempts to pan beyond the PDF page boundaries
- **THEN** the pan stops at the edge of the content

#### Scenario: Pan disabled at fit-to-width
- **WHEN** the PDF zoom level is at or below fit-to-width (100% container width)
- **THEN** single-finger drag performs normal page scroll instead of PDF pan

### Requirement: Touch-action CSS control
The PDF viewer SHALL use appropriate CSS touch-action values to prevent browser gesture conflicts.

#### Scenario: Prevent browser pinch-zoom
- **WHEN** user performs pinch gesture on the PDF viewer
- **THEN** the browser's native page zoom is NOT triggered

#### Scenario: Allow vertical scroll when not zoomed
- **WHEN** the PDF is at fit-to-width zoom level AND user swipes vertically
- **THEN** the page scrolls normally (not intercepted by PDF viewer)
