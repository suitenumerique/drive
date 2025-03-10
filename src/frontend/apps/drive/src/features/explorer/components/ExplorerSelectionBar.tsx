import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { useExplorer } from "./ExplorerContext";

export const ExplorerSelectionBar = () => {
  const { t } = useTranslation();
  const { selectedItems, setSelectedItemIds } = useExplorer();

  const handleClearSelection = () => {
    setSelectedItemIds({});
  };

  return (
    <div className="explorer__selection-bar">
      <div className="explorer__selection-bar__left">
        <div className="explorer__selection-bar__caption">
          {t("explorer.selectionBar.caption", {
            count: selectedItems.length,
          })}
        </div>
        <div className="explorer__selection-bar__actions">
          <Button
            onClick={handleClearSelection}
            icon={<span className="material-icons">download</span>}
            color="primary-text"
            size="small"
            aria-label={t("explorer.selectionBar.download")}
          />
          <Button
            onClick={handleClearSelection}
            icon={<span className="material-icons">arrow_forward</span>}
            color="primary-text"
            size="small"
            aria-label={t("explorer.selectionBar.move")}
          />
          <Button
            onClick={handleClearSelection}
            icon={<span className="material-icons">delete</span>}
            color="primary-text"
            size="small"
            aria-label={t("explorer.selectionBar.delete")}
          />
        </div>
      </div>
      <div className="explorer__selection-bar__actions">
        <Button
          onClick={handleClearSelection}
          icon={<span className="material-icons">close</span>}
          color="primary-text"
          size="small"
          aria-label={t("explorer.selectionBar.reset_selection")}
        />
      </div>
    </div>
  );
};
