import { Button, useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { Item, ItemType } from "@/features/drivers/types";
import { ExplorerCreateFolderModal } from "./modals/ExplorerCreateFolderModal";
import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import uploadFolderSvg from "@/assets/icons/upload_folder.svg";
import createFolderSvg from "@/assets/icons/create_folder.svg";
import createWorkspaceSvg from "@/assets/icons/create_workspace.svg";
import settingsSvg from "@/assets/icons/settings.svg";
import infoSvg from "@/assets/icons/info.svg";
import { ExplorerCreateWorkspaceModal } from "./modals/workspaces/ExplorerCreateWorkspaceModal";
import { useMemo, useState } from "react";
import { ExplorerEditWorkspaceModal } from "./modals/workspaces/ExplorerEditWorkspaceModal";
import { useMutationDeleteWorskpace } from "../hooks/useMutations";
export const ExplorerTree = () => {
  const { t } = useTranslation();

  // itemId is the id of the current item
  const { tree, items, item } = useExplorer();

  const createFolderModal = useModal();
  const createWorkspaceModal = useModal();
  const editWorkspaceModal = useModal();

  const [workspaceToEdit, setWorkspaceToEdit] = useState<Item | undefined>();
  const deleteWorkspaceModal = useMutationDeleteWorskpace();

  const fullTree: Item | undefined = useMemo(() => {
    console.log("tree", tree, "items", items);
    const full: Item = {
      title: "root",
      id: "root",
      type: ItemType.FOLDER,
      filename: "",
      path: "",
      upload_state: "ok",
      updated_at: new Date(),
      children: [],
    };
    if (!tree) {
      return full;
    }

    full.children = [tree];
    if (items) {
      full.children.push(...items.filter((item) => item.id !== tree.id));
    }
    return full;
  }, [tree, items]);

  const drawTreeDuPauvre = (treeItem: Item) => {
    return (
      <div key={treeItem.id}>
        <ExplorerTreeItem
          active={treeItem.id === item?.id}
          item={treeItem}
          onEdit={() => {
            setWorkspaceToEdit(treeItem);
            editWorkspaceModal.open();
          }}
          onDelete={() => {
            deleteWorkspaceModal.mutate(treeItem.id);
          }}
        />
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

  const importMenu = useDropdownMenu();
  const createMenu = useDropdownMenu();

  return (
    <div>
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <DropdownMenu
            options={[
              {
                icon: <img src={createFolderSvg.src} alt="" />,
                label: t("explorer.tree.create.folder"),
                value: "info",
                callback: () => createFolderModal.open(),
              },
              {
                icon: <img src={createWorkspaceSvg.src} alt="" />,
                label: t("explorer.tree.create.workspace"),
                value: "info",
                callback: () => createWorkspaceModal.open(),
              },
            ]}
            {...createMenu}
            onOpenChange={createMenu.setIsOpen}
          >
            <Button
              icon={<span className="material-icons">add</span>}
              onClick={() => createMenu.setIsOpen(true)}
            >
              {t("explorer.tree.create.label")}
            </Button>
          </DropdownMenu>

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
            {...importMenu}
            onOpenChange={importMenu.setIsOpen}
          >
            <Button
              color="secondary"
              onClick={() => importMenu.setIsOpen(true)}
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
        {fullTree && drawTreeDuPauvre(fullTree)}
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} />
      <ExplorerCreateWorkspaceModal {...createWorkspaceModal} />
      {workspaceToEdit && (
        <ExplorerEditWorkspaceModal
          {...editWorkspaceModal}
          item={workspaceToEdit}
          onClose={() => {
            setWorkspaceToEdit(undefined);
            editWorkspaceModal.close();
          }}
        />
      )}
    </div>
  );
};

const ExplorerTreeItem = ({
  item,
  active,
  onEdit,
  onDelete,
}: {
  item: Item;
  active: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) => {
  const { onNavigate } = useExplorer();
  const menu = useDropdownMenu();
  const { t } = useTranslation();
  return (
    <div
      style={{
        fontWeight: active ? "bold" : "normal",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div
        onClick={() =>
          onNavigate({
            type: NavigationEventType.ITEM,
            item: item,
          })
        }
      >
        {item.title}
      </div>

      {item.path?.split(".").length === 1 && (
        <div>
          <DropdownMenu
            options={[
              {
                icon: <img src={infoSvg.src} alt="" />,
                label: t("explorer.tree.workspace.options.info"),
                value: "info",
              },
              {
                icon: <img src={settingsSvg.src} alt="" />,
                label: t("explorer.tree.workspace.options.settings"),
                value: "settings",
                callback: onEdit,
              },
              {
                icon: <span className="material-icons">delete</span>,
                label: t("explorer.tree.workspace.options.delete"),
                value: "delete",
                callback: onDelete,
              },
            ]}
            {...menu}
            onOpenChange={menu.setIsOpen}
          >
            <Button
              icon={<span className="material-icons">more_horiz</span>}
              color="tertiary-text"
              size="small"
              onClick={() => menu.setIsOpen(true)}
            />
          </DropdownMenu>
        </div>
      )}
    </div>
  );
};
