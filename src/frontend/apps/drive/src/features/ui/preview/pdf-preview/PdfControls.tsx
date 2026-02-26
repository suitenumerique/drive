import { Button } from "@gouvfr-lasuite/cunningham-react";
import { LeftSidebarIcon } from "../../components/icon/LeftSidebarIcon";
import { ZoomOut } from "../../components/icon/ZoomOut";
import { ZoomIn } from "../../components/icon/ZoomIn";
import { ZoomReset } from "../../components/icon/ZoomReset";

interface PdfControlsProps {
  currentPage: number;
  numPages: number;
  pageInputValue: string;
  isSidebarOpen: boolean;
  zoom: number;
  onToggleSidebar: () => void;
  onGoToPreviousPage: () => void;
  onGoToNextPage: () => void;
  onPageInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onPageInputSubmit: () => void;
  onPageInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onZoomIn: () => void;
  onZoomReset: () => void;
  onZoomOut: () => void;
}

export function PdfControls({
  currentPage,
  numPages,
  pageInputValue,
  zoom,
  onToggleSidebar,
  onPageInputChange,
  onPageInputSubmit,
  onPageInputKeyDown,
  onZoomIn,
  onZoomReset,
  onZoomOut,
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
      <div className="controls-vertical-separator" />
      <div className="pdf-preview__zoom-controls">
        <Button
          variant="tertiary"
          color="neutral"
          onClick={onZoomOut}
          icon={<ZoomOut />}
          size="small"
        />
        <Button
          variant="tertiary"
          color="neutral"
          onClick={onZoomReset}
          icon={<ZoomReset />}
          size="small"
        />
        <Button
          variant="tertiary"
          color="neutral"
          onClick={onZoomIn}
          icon={<ZoomIn />}
          size="small"
        />
      </div>
    </div>
  );
}
