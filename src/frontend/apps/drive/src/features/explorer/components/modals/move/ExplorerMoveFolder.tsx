import { getDriver } from "@/features/config/Config";
import { Item, ItemType } from "@/features/drivers/types";
import { Button, Modal, ModalSize } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { ExplorerGridItemsList } from "../../grid/ExplorerGrid";
import { useMemo, useState } from "react";
import { NavigationEvent } from "../../ExplorerContext";
import { HorizontalSeparator } from "@gouvfr-lasuite/ui-kit";
import {
  BreadcrumbItem,
  Breadcrumbs,
} from "@/features/ui/components/breadcrumbs/Breadcrumbs";

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
    <Modal
      isOpen={isOpen}
      title="Déplacer"
      onClose={onClose}
      size={ModalSize.LARGE}
      rightActions={
        <>
          <Button color="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button color="primary" onClick={onClose}>
            Déplacer ici
          </Button>
        </>
      }
    >
      <div className="modal__move">
        <span className="modal__move__description">
          Choisissez le nouvel emplacement pour
          <strong> Notes réunion de lundi 17 sept.</strong>
        </span>
        <HorizontalSeparator />
      </div>
      <ExplorerMoveFolderContent itemToMove={itemToMove} />
      <HorizontalSeparator />
    </Modal>
  );
};

interface ExplorerMoveFolderContentProps {
  itemToMove: Item;
}

export const ExplorerMoveFolderContent = ({
  itemToMove,
}: ExplorerMoveFolderContentProps) => {
  const [itemId, setItemId] = useState<string | null>(null);
  const [history, setHistory] = useState<Item[]>([]);

  // Update history when navigating
  const onNavigate = (event: NavigationEvent) => {
    const item = event.item as Item;
    setItemId(item.id);
    setHistory((prev) => [...prev, item]);
  };

  // Add a function to go back in history
  const goBackToItem = (item: Item) => {
    setItemId(item.id);
    setHistory((prev) => prev.slice(0, prev.indexOf(item) + 1));
  };

  const getBreadcrumbsItems = () => {
    const breadcrumbsItems: BreadcrumbItem[] = [
      {
        content: (
          <div
            onClick={() => {
              setItemId(null);
              setHistory([]);
            }}
          >
            Espaces
          </div>
        ),
      },
    ];

    history.forEach((item, index) => {
      breadcrumbsItems.push({
        content: (
          <button
            className="c__breadcrumbs__button"
            onClick={() => goBackToItem(item)}
          >
            {item.title}
          </button>
        ),
      });
    });

    return breadcrumbsItems;
  };

  const breadcrumbsItems = useMemo(() => {
    return getBreadcrumbsItems();
  }, [history]);

  const { data: firstLevelItems } = useQuery({
    queryKey: ["firstLevelItems"],
    queryFn: () => getDriver().getItems(),
  });

  const { data: itemChildren } = useQuery({
    queryKey: ["items", itemId, "children", []],
    enabled: itemId !== null,
    queryFn: () => {
      if (itemId === null) {
        return Promise.resolve(undefined);
      }
      return getDriver().getChildren(itemId, { type: ItemType.FOLDER });
    },
  });

  const items = useMemo(() => {
    let items = [];
    if (itemId === null) {
      items = firstLevelItems ?? [];
    } else {
      items = itemChildren ?? [];
    }

    // Filter out the itemToMove from the items list
    items = items.filter((item) => item.id !== itemToMove.id);
    return items;
  }, [itemId, firstLevelItems, itemChildren]);

  return (
    <div
      style={{ display: "flex", flexDirection: "column", maxHeight: "500px" }}
    >
      <div className="">
        <Breadcrumbs items={breadcrumbsItems} />
      </div>
      <div className="c__datagrid explorer__grid explorer__compact">
        <ExplorerGridItemsList
          isCompact
          items={items}
          gridActionsCell={() => <div />}
          onNavigate={onNavigate}
          //   gridHeader={<div>coucou</div>}
        />
      </div>
    </div>
  );
};
