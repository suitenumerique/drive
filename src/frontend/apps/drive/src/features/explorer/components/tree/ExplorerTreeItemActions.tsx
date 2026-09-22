import { Button } from "@gouvfr-lasuite/ui-components";
import { Item } from "@/features/drivers/types";
import clsx from "clsx";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import { useState } from "react";

import { UseItemActionMenuItemsReturn } from "../../hooks/useItemActionMenuItems";

export type ExplorerTreeItemActionsProps = {
  item: Item;
  getMenuItems: UseItemActionMenuItemsReturn["getMenuItems"];
};
export const ExplorerTreeItemActions = ({
  item,
  getMenuItems,
}: ExplorerTreeItemActionsProps) => {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <div
        className={clsx("explorer__tree__item__actions", {
          "explorer__tree__item__actions--open": isOpen,
        })}
      >
        <ItemActionDropdown
          menuItems={getMenuItems(item, {
            minimal: true,
            itemId: item.originalId ?? item.id,
          })}
          isOpen={isOpen}
          setIsOpen={setIsOpen}
          trigger={
            <Button
              size="nano"
              variant="tertiary"
              onClick={() => setIsOpen(!isOpen)}
              aria-label="more_actions"
              className="explorer__tree__item__actions__button-more"
              icon={<span className="material-icons more">more_horiz</span>}
            />
          }
        />
      </div>
    </>
  );
};
