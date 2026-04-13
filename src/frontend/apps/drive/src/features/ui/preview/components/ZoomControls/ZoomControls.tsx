import { ResetZoomIcon } from "@/features/ui/components/icon/ResetZoomIcon";
import { ZoomMinusIcon } from "@/features/ui/components/icon/ZoomMinusIcon";
import { ZoomPlusIcon } from "@/features/ui/components/icon/ZoomPlusIcon";
import { Button } from "@gouvfr-lasuite/cunningham-react";

interface ZoomControlsProps {
  zoomOut: () => void;
  zoomIn: () => void;
  resetView: () => void;
}

export const ZoomControls = ({
  zoomOut,
  zoomIn,
  resetView,
}: ZoomControlsProps) => {
  return (
    <div className="file-preview__controls__zoom">
      <Button
        variant="tertiary"
        color="neutral"
        size="small"
        onClick={zoomOut}
        icon={<ZoomMinusIcon />}
      />
      <Button
        variant="tertiary"
        color="neutral"
        size="small"
        onClick={resetView}
        icon={<ResetZoomIcon />}
      />
      <Button
        variant="tertiary"
        color="neutral"
        size="small"
        onClick={zoomIn}
        icon={<ZoomPlusIcon />}
      />
    </div>
  );
};
