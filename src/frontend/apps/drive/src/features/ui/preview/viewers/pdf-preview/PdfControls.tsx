import { Button, Input } from "@gouvfr-lasuite/cunningham-react";
import { LeftSidebarIcon } from "../../../components/icon/LeftSidebarIcon";
import { ZoomControls } from "../../components/ZoomControls/ZoomControls";

interface PdfControlsProps {
  numPages: number;
  pageInputValue: string;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onPageInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPageInputSubmit: () => void;
  onPageInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onZoomIn: () => void;
  onZoomReset: () => void;
  onZoomOut: () => void;
}

export function PdfControls({
  numPages,
  pageInputValue,
  onToggleSidebar,
  onPageInputChange,
  onPageInputSubmit,
  onPageInputKeyDown,
  onZoomIn,
  onZoomReset,
  onZoomOut,
}: PdfControlsProps) {
  return (
    <div className="file-preview__controls">
      <Button
        variant="tertiary"
        color="neutral"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
        size="small"
        icon={<LeftSidebarIcon />}
      />
      <div className="file-preview__controls__separator" />
      <div className="pdf-preview__page-nav">
        <div className="pdf-preview__page-indicator">
          <Input
            variant="classic"
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
      <div className="file-preview__controls__separator" />
      <ZoomControls
        zoomOut={onZoomOut}
        zoomIn={onZoomIn}
        resetView={onZoomReset}
      />
    </div>
  );
}
