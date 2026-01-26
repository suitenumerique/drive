import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { Item } from "@/features/drivers/types";
import clsx from "clsx";
import { ItemActionDropdown } from "../item-actions/ItemActionDropdown";
import { useState } from "react";

export type ExplorerTreeItemActionsProps = {
  item: Item;
};
export const ExplorerTreeItemActions = ({
  item,
}: ExplorerTreeItemActionsProps) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <div
        className={clsx("explorer__tree__item__actions", {
          "explorer__tree__item__actions--open": isOpen,
        })}
      >
        <ItemActionDropdown
          item={item}
          itemId={item.originalId ?? item.id}
          isOpen={isOpen}
          minimal={true}
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
