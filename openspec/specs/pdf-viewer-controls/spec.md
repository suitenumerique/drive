### Requirement: Page navigation buttons
The PDF viewer SHALL display previous and next page buttons that allow users to navigate between pages sequentially.

#### Scenario: Navigate to next page
- **WHEN** user clicks the "next page" button
- **THEN** the viewer displays the next page and updates the page indicator

#### Scenario: Navigate to previous page
- **WHEN** user clicks the "previous page" button
- **THEN** the viewer displays the previous page and updates the page indicator

#### Scenario: Next button disabled on last page
- **WHEN** the current page is the last page of the document
- **THEN** the "next page" button SHALL be disabled

#### Scenario: Previous button disabled on first page
- **WHEN** the current page is the first page of the document
- **THEN** the "previous page" button SHALL be disabled

### Requirement: Page jump input
The PDF viewer SHALL display a page input field showing the current page number and total pages, allowing users to jump directly to any page.

#### Scenario: Display current page indicator
- **WHEN** a PDF document is loaded
- **THEN** the viewer displays "X / Y" where X is the current page and Y is the total page count

#### Scenario: Jump to specific page via input
- **WHEN** user enters a valid page number in the input field and presses Enter or blurs the field
- **THEN** the viewer navigates to that page

#### Scenario: Invalid page number handling
- **WHEN** user enters a page number outside the valid range (less than 1 or greater than total pages)
- **THEN** the input value is clamped to the nearest valid page number (1 or total pages)

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
- **THEN** the zoom level resets to 100%

#### Scenario: Zoom bounds enforcement
- **WHEN** user attempts to zoom beyond the minimum (50%) or maximum (200%) bounds
- **THEN** the zoom level remains at the boundary and the respective zoom button is disabled

### Requirement: PDF content centering
The PDF viewer SHALL center the rendered PDF page horizontally within the viewport.

#### Scenario: Centered display
- **WHEN** a PDF page is rendered
- **THEN** the page is horizontally centered in the viewing area

### Requirement: Single page rendering
The PDF viewer SHALL render only the current page rather than all pages simultaneously.

#### Scenario: Initial load
- **WHEN** a PDF document is loaded
- **THEN** only page 1 is rendered initially

#### Scenario: Page change
- **WHEN** user navigates to a different page
- **THEN** only the new current page is rendered

### Requirement: BEM classnames
The PDF viewer SHALL use BEM-convention classnames consistent with other preview components in the application.

#### Scenario: Component classnames
- **WHEN** the PDF viewer is rendered
- **THEN** it uses classnames following the pattern `.pdf-preview`, `.pdf-preview__controls`, `.pdf-preview__page`, etc.
