import { Button, useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { Item } from "@/features/drivers/types";
import { ExplorerCreateFolderModal } from "./modals/ExplorerCreateFolderModal";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useState } from "react";
import folderSvg from "@/assets/icons/folder.svg";
import workspaceSvg from "@/assets/icons/workspace.svg";

export const ExplorerTree = () => {
  const { t } = useTranslation();

  // itemId is the id of the current item
  const { item, tree, onNavigate } = useExplorer();

  const createFolderModal = useModal();

  const drawTreeDuPauvre = (treeItem: Item) => {
    return (
      <div key={treeItem.id}>
        <div
          style={{
            fontWeight: treeItem.id === item?.id ? "bold" : "normal",
            cursor: "pointer",
          }}
          onClick={() =>
            onNavigate({
              type: NavigationEventType.ITEM,
              item: treeItem,
            })
          }
        >
          {treeItem.title}
        </div>
        <div
          style={{
            paddingLeft: "2rem",
          }}
        >
          {treeItem.children?.map((child) => drawTreeDuPauvre(child))}
        </div>
      </div>
    );
  };

  const [isCreateDropdownOpen, setIsCreateDropdownOpen] = useState(false);

  return (
    <div>
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <DropdownMenu
            options={[
              {
                icon: <img src={folderSvg.src} alt="" />,
                label: t("explorer.tree.createFolderDropdown.createFolder"),
                value: "info",
                callback: createFolderModal.open,
              },
              {
                icon: <img src={workspaceSvg.src} alt="" />,
                label: t("explorer.tree.createFolderDropdown.createWorkspace"),
                value: "info",
                callback: createFolderModal.open,
              },
            ]}
            isOpen={isCreateDropdownOpen}
            onOpenChange={setIsCreateDropdownOpen}
          >
            <Button
              icon={<span className="material-icons">add</span>}
              onClick={() => setIsCreateDropdownOpen(!isCreateDropdownOpen)}
            >
              {t("explorer.tree.createFolder")}
            </Button>
          </DropdownMenu>
          <Button color="secondary">{t("explorer.tree.import")}</Button>
        </div>
        <Button
          color="primary-text"
          aria-label={t("explorer.tree.search")}
          icon={<span className="material-icons">search</span>}
        ></Button>
      </div>
      <div
        style={{
          padding: "12px",
        }}
      >
        {tree && drawTreeDuPauvre(tree)}
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} />
    </div>
  );
};
