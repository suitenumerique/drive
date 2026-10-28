import { Button } from "@gouvfr-lasuite/ui-components";
import { More } from "@gouvfr-lasuite/ui-components/icons";
import { Item } from "@/features/drivers/types";
import clsx from "clsx";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import { useState } from "react";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
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
              aria-label={t("explorer.grid.actions.button_aria_label", {
                name: item.title,
              })}
              className="explorer__tree__item__actions__button-more"
              icon={<More size={16} aria-hidden="true" />}
            />
          }
        />
      </div>
    </>
  );
};
