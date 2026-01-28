## ADDED Requirements

### Requirement: Responsive PDF width
The PDF viewer SHALL render the PDF at a width appropriate for the current viewport, fitting within the container on mobile devices.

#### Scenario: Mobile viewport initial render
- **WHEN** the PDF viewer container width is less than 768px
- **THEN** the PDF page renders at the container width (minus padding) instead of the fixed 800px width

#### Scenario: Desktop viewport initial render
- **WHEN** the PDF viewer container width is 768px or greater
- **THEN** the PDF page renders at 800px width (existing behavior)

#### Scenario: Container resize
- **WHEN** the viewport or container is resized (e.g., device rotation, window resize)
- **THEN** the PDF width adjusts accordingly to fit the new container size

### Requirement: Fit-to-width on mobile load
The PDF viewer SHALL display the entire PDF width on initial load on mobile devices without horizontal overflow.

#### Scenario: No horizontal overflow on mobile
- **WHEN** a PDF loads on a mobile device (container width < 768px)
- **THEN** the PDF is fully visible horizontally without requiring horizontal scroll

#### Scenario: Zoom level reflects fit-to-width
- **WHEN** the PDF loads at fit-to-width on mobile
- **THEN** the zoom indicator displays 100%

## MODIFIED Requirements

### Requirement: Zoom controls
The PDF viewer SHALL display zoom in, zoom out buttons and a zoom percentage indicator, allowing users to adjust the document scale.

#### Scenario: Zoom in
- **WHEN** user clicks the "zoom in" button
- **THEN** the PDF scale increases by one zoom step (25%) and the percentage display updates

#### Scenario: Zoom out
- **WHEN** user clicks the "zoom out" button
- **THEN** the PDF scale decreases by one zoom step (25%) and the percentage display updates

#### Scenario: Zoom percentage display
- **WHEN** the zoom level changes
- **THEN** the zoom percentage indicator displays the current zoom level as a percentage (e.g., "100%")

#### Scenario: Reset zoom on percentage click
- **WHEN** user clicks the zoom percentage indicator
- **THEN** the zoom level resets to 100% (fit-to-width on mobile, 800px on desktop)

#### Scenario: Zoom bounds enforcement
- **WHEN** user attempts to zoom beyond the minimum (50%) or maximum (200%) bounds
- **THEN** the zoom level remains at the boundary and the respective zoom button is disabled

#### Scenario: Zoom works with responsive base width
- **WHEN** user zooms on mobile where base width is container width
- **THEN** zoom percentages are calculated relative to the responsive base width (e.g., 150% = 1.5x container width)
