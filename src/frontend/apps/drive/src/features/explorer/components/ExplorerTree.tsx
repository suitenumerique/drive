import { Button, useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { Item } from "@/features/drivers/types";
import { ExplorerCreateFolderModal } from "./modals/ExplorerCreateFolderModal";
import { useState } from "react";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import uploadFolderSvg from "@/assets/icons/upload_folder.svg";

export const ExplorerTree = () => {
  const { t } = useTranslation();

  // itemId is the id of the current item
  const { item, tree, onNavigate, dropZone } = useExplorer();

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

  const [isImportDropdownOpen, setIsImportDropdownOpen] = useState(false);

  return (
    <div>
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <Button
            icon={<span className="material-icons">add</span>}
            onClick={createFolderModal.open}
          >
            {t("explorer.tree.createFolder")}
          </Button>

          <DropdownMenu
            options={[
              {
                icon: <img src={uploadFileSvg.src} alt="" />,
                label: t("explorer.tree.import.files"),
                value: "info",
                callback: () => {
                  document.getElementById("import-files")?.click();
                },
              },
              {
                icon: <img src={uploadFolderSvg.src} alt="" />,
                label: t("explorer.tree.import.folders"),
                value: "info",
                callback: () => {
                  document.getElementById("import-folders")?.click();
                },
              },
            ]}
            isOpen={isImportDropdownOpen}
            onOpenChange={setIsImportDropdownOpen}
          >
            <Button
              color="secondary"
              onClick={() => setIsImportDropdownOpen(true)}
            >
              {t("explorer.tree.import.label")}
            </Button>
          </DropdownMenu>
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
