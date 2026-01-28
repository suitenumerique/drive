## 1. Refactor Component Structure

- [x] 1.1 Replace placeholder classnames ("Example") with BEM classnames (`.pdf-preview`, `.pdf-preview__container`, `.pdf-preview__page`)
- [x] 1.2 Update SCSS file with BEM structure and flexbox centering for the container
- [x] 1.3 Change from rendering all pages to rendering only the current page (add `currentPage` state, render single `<Page>`)

## 2. Page Navigation Controls

- [x] 2.1 Add `currentPage` state initialized to 1
- [x] 2.2 Create previous/next page buttons using `Button` from `@openfun/cunningham-react` and `Icon` from `@gouvfr-lasuite/ui-kit`
- [x] 2.3 Implement `goToNextPage` and `goToPreviousPage` handlers with boundary checks
- [x] 2.4 Disable previous button when on page 1, disable next button when on last page

## 3. Page Jump Input

- [x] 3.1 Add page input field displaying current page number
- [x] 3.2 Display total pages as "X / Y" format next to input
- [x] 3.3 Implement page jump on Enter key or blur with validation (clamp to 1-numPages range)

## 4. Zoom Controls

- [x] 4.1 Add `zoom` state initialized to 1 (100%)
- [x] 4.2 Import and use `ZoomControl` component from ImageViewer
- [x] 4.3 Implement `zoomIn`, `zoomOut`, and `resetZoom` handlers with 0.25 step and 0.5-2.0 bounds
- [x] 4.4 Apply zoom to Page component width (`baseWidth * zoom`)

## 5. Control Bar Layout

- [x] 5.1 Create `.pdf-preview__controls` container below the PDF content
- [x] 5.2 Layout page navigation on the left, vertical separator, zoom controls on the right
- [x] 5.3 Style controls bar consistent with other preview components (VideoPlayer, ImageViewer)

## 6. Cleanup

- [x] 6.1 Remove `console.log` statement from PDF fetch code
- [x] 6.2 Remove unused `containerWidth` state and commented code
