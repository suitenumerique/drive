import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon } from "@gouvfr-lasuite/ui-kit";

interface PdfControlsProps {
  currentPage: number;
  numPages: number;
  pageInputValue: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onGoToPreviousPage: () => void;
  onGoToNextPage: () => void;
  onPageInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPageInputSubmit: () => void;
  onPageInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}

export function PdfControls({
  currentPage,
  numPages,
  pageInputValue,
  isSidebarOpen,
  onToggleSidebar,
  onGoToPreviousPage,
  onGoToNextPage,
  onPageInputChange,
  onPageInputSubmit,
  onPageInputKeyDown,
}: PdfControlsProps) {
  return (
    <div className="pdf-preview__controls">
      <Button
        variant="tertiary"
        color="neutral"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
      >
        <Icon name="view_sidebar" />
      </Button>
      <div className="controls-vertical-separator" />
      <div className="pdf-preview__page-nav">
        <Button
          variant="tertiary"
          color="neutral"
          onClick={onGoToPreviousPage}
          disabled={currentPage <= 1}
          aria-label="Previous page"
        >
          <Icon name="chevron_left" />
        </Button>
        <div className="pdf-preview__page-indicator">
          <input
            type="text"
            className="pdf-preview__page-input"
            value={pageInputValue}
            onChange={onPageInputChange}
            onBlur={onPageInputSubmit}
            onKeyDown={onPageInputKeyDown}
            aria-label="Current page"
          />
          <span className="pdf-preview__page-total">/ {numPages}</span>
        </div>
        <Button
          variant="tertiary"
          color="neutral"
          onClick={onGoToNextPage}
          disabled={currentPage >= numPages}
          aria-label="Next page"
        >
          <Icon name="chevron_right" />
        </Button>
      </div>
    </div>
  );
}
