import { Button } from "@gouvfr-lasuite/cunningham-react";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { LeftSidebarIcon } from "../../components/icon/LeftSidebarIcon";

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
        size="small"
        icon={<LeftSidebarIcon />}
      />
      <div className="controls-vertical-separator" />
      <div className="pdf-preview__page-nav">
        <div className="pdf-preview__page-indicator">
          <input
            type="text"
            className="pdf-preview__page-input"
            value={pageInputValue}
            onChange={onPageInputChange}
            onBlur={onPageInputSubmit}
            onKeyDown={onPageInputKeyDown}
            aria-label="Current page"
            size={pageInputValue.length || 1}
          />
          <span className="pdf-preview__page-total">/ {numPages}</span>
        </div>
      </div>
    </div>
  );
}
