import { Button, useModal } from "@openfun/cunningham-react";
import { ExplorerSearchModal } from "@/features/explorer/components/modals/search/ExplorerSearchModal";
import { useTranslation } from "react-i18next";
import { useEffect } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
export const ExplorerSearchButton = ({
  keyboardShortcut,
  defaultFilters,
}: {
  keyboardShortcut?: boolean;
  defaultFilters?: ItemFilters;
}) => {
  const searchModal = useModal();
  const { t } = useTranslation();

  // Toggle the menu when ⌘K is pressed
  useEffect(() => {
    if (!keyboardShortcut) {
      return;
    }
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        searchModal.open();
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [keyboardShortcut]);

  return (
    <>
      <ExplorerSearchModal {...searchModal} defaultFilters={defaultFilters} />

      <Button
        variant="tertiary"
        aria-label={t("explorer.tree.search")}
        icon={<span className="material-icons">search</span>}
        onClick={searchModal.open}
      />
    </>
  );
};
