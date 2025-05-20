import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { Modal, ModalSize } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { ExplorerGridItemsList } from "../../grid/ExplorerGrid";

interface ExplorerMoveFolderProps {
  isOpen: boolean;
  onClose: () => void;
  itemToMove: Item;
}

export const ExplorerMoveFolder = ({
  isOpen,
  onClose,
  itemToMove,
}: ExplorerMoveFolderProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size={ModalSize.LARGE}>
      <ExplorerMoveFolderContent itemToMove={itemToMove} />
    </Modal>
  );
};

interface ExplorerMoveFolderContentProps {
  itemToMove: Item;
}

export const ExplorerMoveFolderContent = ({
  itemToMove,
}: ExplorerMoveFolderContentProps) => {
  const { data: firstLevelItems } = useQuery({
    queryKey: ["firstLevelItems"],
    queryFn: () => getDriver().getItems(),
  });

  return (
    <div className="c__datagrid explorer__grid explorer__compact">
      <ExplorerGridItemsList
        isCompact
        items={firstLevelItems ?? []}
        gridActionsCell={() => <div />}
        onNavigate={(e) => {
          console.log(e);
        }}
        //   gridHeader={<div>coucou</div>}
      />
    </div>
  );
};
