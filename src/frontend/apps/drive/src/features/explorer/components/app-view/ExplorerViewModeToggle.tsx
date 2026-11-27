import { Button } from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { useAppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { ViewMode } from "../../hooks/useViewMode";

const VIEW_MODE_ICONS: Record<ViewMode, string> = {
  list: "view_list",
  grid: "grid_view",
};

export const ExplorerViewModeToggle = () => {
  const { t } = useTranslation();
  const { viewMode, onViewModeChange } = useAppExplorer();

  return (
    <div
      className="explorer__view-mode"
      role="group"
      aria-label={t("explorer.viewMode.label")}
    >
      {(Object.keys(VIEW_MODE_ICONS) as ViewMode[]).map((mode) => (
        <Button
          key={mode}
          variant="tertiary"
          color="neutral"
          size="small"
          active={viewMode === mode}
          aria-pressed={viewMode === mode}
          aria-label={t(`explorer.viewMode.${mode}`)}
          icon={
            <span className="material-icons" aria-hidden="true">
              {VIEW_MODE_ICONS[mode]}
            </span>
          }
          onClick={() => onViewModeChange(mode)}
        />
      ))}
    </div>
  );
};
