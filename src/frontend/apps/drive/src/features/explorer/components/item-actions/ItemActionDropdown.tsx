import { DropdownMenu, MenuItem } from "@gouvfr-lasuite/ui-components";

export type ItemActionDropdownProps = {
  menuItems: MenuItem[];
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  trigger: React.ReactNode;
};

export const ItemActionDropdown = ({
  menuItems,
  isOpen,
  setIsOpen,
  trigger,
}: ItemActionDropdownProps) => (
  <DropdownMenu
    options={menuItems}
    isOpen={isOpen}
    onOpenChange={setIsOpen}
  >
    {trigger}
  </DropdownMenu>
);
