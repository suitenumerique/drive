import { Item } from "@/features/drivers/types";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { useItemActionMenuItems } from "../../hooks/useItemActionMenuItems";

export type ItemActionDropdownProps = {
  item: Item;
  itemId?: string;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  trigger: React.ReactNode;
  onModalOpenChange?: (isModalOpen: boolean) => void;
  minimal?: boolean;
  allowCreate?: boolean;
};

export const ItemActionDropdown = ({
  item,
  itemId,
  isOpen,
  setIsOpen,
  trigger,
  onModalOpenChange,
  minimal = false,
  allowCreate = false,
}: ItemActionDropdownProps) => {
  const { getMenuItems, modals } = useItemActionMenuItems({
    onModalOpenChange,
  });
  const menuItems = getMenuItems(item, { minimal, itemId, allowCreate });

  return (
    <>
      <DropdownMenu options={menuItems} isOpen={isOpen} onOpenChange={setIsOpen}>
        {trigger}
      </DropdownMenu>
      {modals}
    </>
  );
};
